"""Generate an offline PDF flight report from a SCAF telemetry session.

Run from repository root:
  python -m plugins.flight_report.python.src.generate_report data/sessions/SESSION_ID
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean


def finite_number(value):
    """Return float for finite numeric telemetry values, otherwise None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    
    value = float(value)

    return value if math.isfinite(value) else None


def get_nested(obj, *keys):
    for key in keys:
        if not isinstance(obj, dict):
            return None
        
        obj = obj.get(key)

    return obj


def read_session(session_dir: Path):
    telemetry_file = session_dir / 'telemetry.jsonl'
    if not telemetry_file.is_file():
        raise FileNotFoundError(f'Missing {telemetry_file}')
    
    meta_file = session_dir / 'metadata.json'
    meta = json.loads(meta_file.read_text(encoding='utf-8')) if meta_file.exists() else {}
    rows = []
    errors = []

    for line_number, line in enumerate(telemetry_file.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            packet = obj.get('packet', obj)
            if not isinstance(packet, dict) or packet.get('protocol') != 'scaf.telemetry' or packet.get('version') != 1 or packet.get('type') != 'aircraft.state':
                raise ValueError('unsupported telemetry packet')
            
            timestamp = finite_number(packet.get('timestamp'))
            if timestamp is None:
                raise ValueError('missing/invalid timestamp')
            
            data = packet.get('data')
            if not isinstance(data, dict):
                raise ValueError('missing data')
            
            rows.append({
                'time_s': timestamp,
                'sequence': packet.get('sequence'),
                'received_at_utc': obj.get('received_at_utc'),
                'aircraft_type': get_nested(packet, 'aircraft', 'type'),
                'speed_mps': finite_number(data.get('speed_mps')),
                'altitude_m': finite_number(data.get('altitude_m')),
                'fuel_internal_kg': finite_number(data.get('fuel_internal_kg')),
                'fuel_external_kg': finite_number(data.get('fuel_external_kg')),
                'normal_g': finite_number(get_nested(data, 'acceleration_g', 'y')),
                'lat_deg': finite_number(get_nested(data, 'position', 'lat_deg')),
                'lon_deg': finite_number(get_nested(data, 'position', 'lon_deg')),
            })
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f'line {line_number}: {exc}')
    if not rows:
        raise ValueError('No valid aircraft.state records in telemetry.jsonl')
    
    # Preserve input order for sequence loss detection; use chronological sort for plotting.
    sequences = [r['sequence'] for r in rows if type(r['sequence']) is int]
    sequence_gaps = sum(max(0, b - a - 1) for a, b in zip(sequences, sequences[1:]) if b > a)
    sequence_duplicates = sum(b == a for a, b in zip(sequences, sequences[1:]))
    nonmonotonic_time = sum(b['time_s'] < a['time_s'] for a, b in zip(rows, rows[1:]))
    rows.sort(key=lambda r: r['time_s'])

    return meta, rows, {'invalid_lines': len(errors), 'invalid_line_examples': errors[:5],
                        'sequence_gaps': sequence_gaps, 'sequence_duplicates': sequence_duplicates,
                        'time_resets': nonmonotonic_time}


def haversine_km(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    
    return 6371.0088 * (2 * math.atan2(math.sqrt(x), math.sqrt(max(0, 1-x))))


def summarize(meta, rows, quality):
    def numeric(name):
        return [r[name] for r in rows if r[name] is not None]
    
    speeds, alts, gs = numeric('speed_mps'), numeric('altitude_m'), numeric('normal_g')
    fuel = [(r['time_s'], r['fuel_internal_kg'], r['fuel_external_kg']) for r in rows if r['fuel_internal_kg'] is not None]
    fuel_start = fuel[0][1] if fuel else None
    fuel_end = fuel[-1][1] if fuel else None

    # Ignore abrupt position changes and invalid coord pairs; total distance is an estimate.
    track = [(r['time_s'], r['lat_deg'], r['lon_deg']) for r in rows if r['lat_deg'] is not None and r['lon_deg'] is not None and -90 <= r['lat_deg'] <= 90 and -180 <= r['lon_deg'] <= 180]
    distance_km = 0.0
    dropped_segments = 0

    for a, b in zip(track, track[1:]):
        dt = b[0] - a[0]
        d = haversine_km((a[1], a[2]), (b[1], b[2]))
        if 0 < dt <= 5 and d / (dt / 3600) <= 1800:
            distance_km += d
        else:
            dropped_segments += 1

    duration = max(0, rows[-1]['time_s'] - rows[0]['time_s'])

    def exposure(predicate):
        total = 0.0
        for a, b in zip(rows, rows[1:]):
            dt = b['time_s'] - a['time_s']
            if 0 < dt <= 1 and a['normal_g'] is not None and predicate(a['normal_g']):
                total += dt
        return round(total, 2)
    
    summary = {
        'session_id': meta.get('session_id', 'unknown'),
        'aircraft_type': meta.get('aircraft_type') or rows[0]['aircraft_type'] or 'unknown',
        'record_count': len(rows), 'duration_s': round(duration, 2),
        'started_at_utc': meta.get('started_at_utc') or rows[0]['received_at_utc'],
        'completed': bool(meta.get('completed', False)),
        'min_speed_kmh': min(speeds)*3.6 if speeds else None,
        'max_speed_kmh': max(speeds)*3.6 if speeds else None,
        'mean_speed_kmh': mean(speeds)*3.6 if speeds else None,
        'min_altitude_m': min(alts) if alts else None,
        'max_altitude_m': max(alts) if alts else None,
        'min_normal_g': min(gs) if gs else None,
        'max_normal_g': max(gs) if gs else None,
        'time_over_3g_s': exposure(lambda g: g > 3),
        'time_under_0g_s': exposure(lambda g: g < 0),
        'fuel_start_kg': fuel_start, 'fuel_end_kg': fuel_end,
        'fuel_used_kg': max(0, fuel_start - fuel_end) if fuel_start is not None and fuel_end is not None else None,
        'track_distance_estimate_km': round(distance_km, 3) if len(track) > 1 else None,
        'track_points': len(track), 'track_skipped_segments': dropped_segments,
        'data_quality': quality,
    }

    return summary

def save_csv(rows, path):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def draw_charts(rows, out_dir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    charts = []
    series = [
        ('Vitesse', 'speed_mps', 'km/h', 3.6, 'speed.png'),
        ('Altitude', 'altitude_m', 'm', 1.0, 'altitude.png'),
        ('Carburant interne', 'fuel_internal_kg', 'kg', 1.0, 'fuel.png'),
        ('Facteur de charge normal', 'normal_g', 'g', 1.0, 'g_force.png'),
    ]
    for title, field, unit, factor, filename in series:
        pts = [(r['time_s'] - rows[0]['time_s'], r[field] * factor) for r in rows if r[field] is not None]
        if not pts:
            continue

        fig, ax = plt.subplots(figsize=(9, 3.3))
        ax.plot(*zip(*pts), linewidth=1.7)
        ax.set(title=title, xlabel='Temps (s)', ylabel=unit)
        ax.grid(alpha=0.25)

        if field == 'normal_g':
            ax.axhline(0, linestyle='--', linewidth=0.8, color='gray')

        fig.tight_layout()
        fp = out_dir / filename
        fig.savefig(fp, dpi=170)
        plt.close(fig)
        charts.append((title, fp))

    track = [(r['lat_deg'], r['lon_deg']) for r in rows if r['lat_deg'] is not None and r['lon_deg'] is not None and -90 <= r['lat_deg'] <= 90 and -180 <= r['lon_deg'] <= 180]
    
    if len(track) >= 2:
        lats, lons = zip(*track)
        fig, ax = plt.subplots(figsize=(9, 4.2))
        ax.plot(lons, lats, linewidth=1.4)
        ax.scatter([lons[0]], [lats[0]], label='Start', marker='o', s=65)
        ax.scatter([lons[-1]], [lats[-1]], label='End', marker='X', s=65)
        ax.set(xlabel='Longitude (degrés)', ylabel='Latitude (degrés)', title='Trajectoire au sol (coordonnées géographiques)')
        ax.grid(alpha=0.25)
        ax.legend()
        
        # Approximate equal physical scales near current latitude.
        ax.set_aspect(1.0 / max(0.1, math.cos(math.radians(mean(lats)))), adjustable='datalim')
        fig.tight_layout()
        fp = out_dir / 'track.png'
        fig.savefig(fp, dpi=170)
        plt.close(fig)
        charts.append(('Trajectoire au sol', fp))

    return charts


def make_pdf(summary, charts, pdf_path):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SCAFTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=colors.HexColor('#172033'), spaceAfter=10))
    styles.add(ParagraphStyle(name='SmallNote', parent=styles['Normal'], fontSize=8.5, leading=12, textColor=colors.HexColor('#556274')))
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, rightMargin=1.65*cm, leftMargin=1.65*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = [Paragraph('SCAF / RAPPORT DE VOL', styles['SCAFTitle']), Paragraph(f"Session: {summary['session_id']}", styles['Normal']), Spacer(1, 10)]
    
    def fmt(key, precision=2, suffix=''):
        val = summary.get(key)
        return 'N/A' if val is None else f'{val:,.{precision}f}{suffix}'
    
    fields = [
        ('Avion', str(summary['aircraft_type'])),
        ('Départ (UTC)', str(summary['started_at_utc'] or 'Unknown')),
        ('Statut de la session', 'Réussie' if summary['completed'] else 'Non terminé / metadata non finalisée'),
        ('Durée de vol', fmt('duration_s', 1, ' s')),
        ('Échantillons valides', str(summary['record_count'])),
        ('Vitesse indiquée min. / max.', fmt('min_speed_kmh', 1) + ' / ' + fmt('max_speed_kmh', 1) + ' km/h'),
        ('Altitude min / max', fmt('min_altitude_m', 0) + ' / ' + fmt('max_altitude_m', 0) + ' m'),
        ('Normal G min / max', fmt('min_normal_g') + ' / ' + fmt('max_normal_g') + ' g'),
        ('Durée d\'exposition à une accélération supérieure à +3 G', fmt('time_over_3g_s', 2, ' s')),
        ('Durée à une accélération inférieure à 0 G', fmt('time_under_0g_s', 2, ' s')),
        ('Consommation interne de carburant', fmt('fuel_used_kg', 2, ' kg')),
        ('Distance au sol (estimation)', fmt('track_distance_estimate_km', 2, ' km')),
    ]

    table = Table([[Paragraph(a, styles['Normal']), Paragraph(b, styles['Normal'])] for a, b in fields], colWidths=[6.8*cm, 9.3*cm], hAlign='LEFT')
    table.setStyle(TableStyle([('ROWBACKGROUNDS', (0,0),(-1,-1),[colors.white,colors.HexColor('#F3F6FA')]), ('VALIGN',(0,0),(-1,-1),'MIDDLE'), ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    story += [table, Spacer(1, 12), Paragraph('Qualité des données', styles['Heading2'])]
    quality = summary['data_quality']
    story.append(Paragraph(f"Lignes invalides: {quality['invalid_lines']} | Nombres de séquences manquantes: {quality['sequence_gaps']} | Nombres de séquences dupliquées: {quality['sequence_duplicates']} | Reinitialisations du temps de simulation: {quality['time_resets']} | Segments de piste ignorés: {summary['track_skipped_segments']}", styles['SmallNote']))
    story.append(Spacer(1, 8))
    story.append(Spacer(1, 12))
    
    for title, chart_file in charts:
        img = Image(str(chart_file))
        max_w, max_h = 16.4 * cm, 8.1 * cm
        s = min(max_w/img.imageWidth, max_h/img.imageHeight)
        img.drawWidth, img.drawHeight = img.imageWidth*s, img.imageHeight*s
        story.append(KeepTogether([Paragraph(title, styles['Heading2']), img, Spacer(1, 6)]))
    
    def page_footer(canvas, doc_):
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#7A8492'))
        canvas.drawString(1.65*cm, 1.0*cm, 'SCAF - ENSC')
        canvas.drawRightString(A4[0]-1.65*cm, 1.0*cm, f'Page {doc_.page}')
    
    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)


def generate(session_dir: Path, output_dir: Path | None = None):
    meta, rows, quality = read_session(session_dir)
    summary = summarize(meta, rows, quality)
    out = output_dir or (session_dir / 'report')
    out.mkdir(parents=True, exist_ok=True)
    save_csv(rows, out / 'telemetry.csv')
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    charts = draw_charts(rows, out)
    pdf_path = out / 'flight_report.pdf'
    make_pdf(summary, charts, pdf_path)

    return pdf_path, summary


def main():
    ap = argparse.ArgumentParser(description='SCAF flight report generator (offline)')
    ap.add_argument('session_dir', type=Path, help='Directory containing telemetry.jsonl and metadata.json')
    ap.add_argument('--output-dir', type=Path, default=None, help='Output directory (default: SESSION/report)')
    args = ap.parse_args()
    pdf_path, summary = generate(args.session_dir, args.output_dir)
    print(f'Created {pdf_path} ({summary["record_count"]} samples, {summary["duration_s"]} s)')

if __name__ == '__main__':
    main()