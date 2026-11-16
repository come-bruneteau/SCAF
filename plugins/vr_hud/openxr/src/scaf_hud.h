// SCAF VR-005.1: compact transparent head-locked OpenXR HUD with smoothed attitude.
// Adapted to the VR-003 OpenXR-Layer-Template integration, Windows x64 / D3D11.
// No network call is allowed to block the DCS OpenXR frame thread.
#pragma once

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <d3d11_1.h>
#pragma comment(lib, "Ws2_32.lib")

namespace scaf {

constexpr int kMissing = (std::numeric_limits<std::int32_t>::min)();
constexpr std::chrono::seconds kStaleAfter{2};

#pragma pack(push, 1)
struct WireData {
    char magic[4];
    std::uint32_t sequence;
    std::int32_t speedKmh;
    std::int32_t altitudeM;
    std::int32_t fuelKg;
    std::int32_t normalGCentis;
};
#pragma pack(pop)
static_assert(sizeof(WireData) == 24, "SCAF SHD1 packet layout must be 24 bytes");

#pragma pack(push, 1)
struct WireDataV2 {
    WireData base;
    std::int32_t pitchCentideg;
    std::int32_t bankCentideg;
};
#pragma pack(pop)
static_assert(sizeof(WireDataV2) == 32, "SCAF SHD2 packet layout must be 32 bytes");

struct LiveData {
    bool fresh{false};
    std::int32_t speedKmh{kMissing};
    std::int32_t altitudeM{kMissing};
    std::int32_t fuelKg{kMissing};
    std::int32_t normalGCentis{kMissing};
    std::int32_t pitchCentideg{kMissing};
    std::int32_t bankCentideg{kMissing};
};

class LocalReceiver {
public:
    LocalReceiver() {
        WSADATA wsa{};
        if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return;
        initialized_ = true;
        socket_ = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (socket_ == INVALID_SOCKET) return;
        u_long nonblocking = 1;
        if (ioctlsocket(socket_, FIONBIO, &nonblocking) != 0) return;
        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(50502);
        addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        if (bind(socket_, reinterpret_cast<const sockaddr*>(&addr), sizeof(addr)) != 0) return;
        ready_ = true;
    }

    LocalReceiver(const LocalReceiver&) = delete;
    LocalReceiver& operator=(const LocalReceiver&) = delete;

    ~LocalReceiver() {
        if (socket_ != INVALID_SOCKET) closesocket(socket_);
        if (initialized_) WSACleanup();
    }

    LiveData poll() {
        // Bound work per XR frame. UDP socket is nonblocking; drop old packets.
        if (ready_) {
            for (int i = 0; i < 32; ++i) {
                std::array<char, 256> buffer{};
                const int size = recvfrom(socket_, buffer.data(), static_cast<int>(buffer.size()), 0, nullptr, nullptr);
                if (size == SOCKET_ERROR) {
                    if (WSAGetLastError() == WSAEWOULDBLOCK) break;
                    break;
                }
                if (size != static_cast<int>(sizeof(WireData)) &&
                    size != static_cast<int>(sizeof(WireDataV2))) continue;
                WireData next{};
                std::memcpy(&next, buffer.data(), sizeof(next));
                const bool v1 = size == sizeof(WireData) && std::memcmp(next.magic, "SHD1", 4) == 0;
                const bool v2 = size == sizeof(WireDataV2) && std::memcmp(next.magic, "SHD2", 4) == 0;
                if (!v1 && !v2) continue;
                last_.pitchCentideg = kMissing;
                last_.bankCentideg = kMissing;
                if (v2) {
                    WireDataV2 extended{};
                    std::memcpy(&extended, buffer.data(), sizeof(extended));
                    last_.pitchCentideg = extended.pitchCentideg;
                    last_.bankCentideg = extended.bankCentideg;
                }
                last_.speedKmh = next.speedKmh;
                last_.altitudeM = next.altitudeM;
                last_.fuelKg = next.fuelKg;
                last_.normalGCentis = next.normalGCentis;
                lastUpdate_ = std::chrono::steady_clock::now();
                everReceived_ = true;
            }
        }
        LiveData result = last_;
        result.fresh = everReceived_ &&
            (std::chrono::steady_clock::now() - lastUpdate_ <= kStaleAfter);
        return result;
    }

private:
    SOCKET socket_{INVALID_SOCKET};
    bool initialized_{false};
    bool ready_{false};
    bool everReceived_{false};
    LiveData last_{};
    std::chrono::steady_clock::time_point lastUpdate_{};
};

inline void Rect(ID3D11DeviceContext1* context, ID3D11RenderTargetView* target,
                 int x, int y, int width, int height, int maxWidth, int maxHeight,
                 const float (&color)[4]) {
    if (width <= 0 || height <= 0) return;
    const int l = (std::max)(0, x);
    const int t = (std::max)(0, y);
    const int r = (std::min)(maxWidth, x + width);
    const int b = (std::min)(maxHeight, y + height);
    if (l >= r || t >= b) return;
    D3D11_RECT bounds{l, t, r, b};
    context->ClearView(target, color, &bounds, 1);
}

inline void Digit(ID3D11DeviceContext1* context, ID3D11RenderTargetView* target,
                  int x, int y, int digit, int w, int h, int maxWidth, int maxHeight,
                  const float (&color)[4]) {
    constexpr std::array<unsigned char, 10> patterns = {
        0b1111110, 0b0110000, 0b1101101, 0b1111001, 0b0110011,
        0b1011011, 0b1011111, 0b1110000, 0b1111111, 0b1111011};
    const int s = (std::max)(2, w / 8);
    const int half = h / 2;
    const auto rect = [&](int dx, int dy, int rw, int rh) {
        Rect(context, target, x + dx, y + dy, rw, rh, maxWidth, maxHeight, color);
    };
    if (digit == -1) { // minus sign
        rect(s, half - s / 2, w - 2 * s, s);
        return;
    }
    if (digit == -2) { // unavailable data
        rect(s, half - s / 2, w - 2 * s, s);
        return;
    }
    if (digit < 0 || digit > 9) return;
    const auto pattern = patterns[digit];
    if (pattern & 0b1000000) rect(s, 0, w - 2 * s, s);
    if (pattern & 0b0100000) rect(w - s, s, s, half - s);
    if (pattern & 0b0010000) rect(w - s, half, s, half - s);
    if (pattern & 0b0001000) rect(s, h - s, w - 2 * s, s);
    if (pattern & 0b0000100) rect(0, half, s, half - s);
    if (pattern & 0b0000010) rect(0, s, s, half - s);
    if (pattern & 0b0000001) rect(s, half - s/2, w - 2 * s, s);
}

inline void DrawNumber(ID3D11DeviceContext1* context, ID3D11RenderTargetView* target,
                       int x, int y, std::int32_t value, int digits, bool signedValue,
                       bool available, int maxWidth, int maxHeight, const float (&color)[4]) {
    constexpr int kWidth = 23;
    constexpr int kHeight = 40;
    constexpr int kStep = 31;
    const bool negative = signedValue && value < 0 && value != kMissing;
    if (signedValue && negative) {
        Digit(context, target, x - 27, y, -1, kWidth, kHeight, maxWidth, maxHeight, color);
    }
    const bool valid = available && value != kMissing && value > -1000000 && value < 1000000;
    std::uint32_t magnitude = valid ? static_cast<std::uint32_t>(negative ? -value : value) : 0;
    const std::uint32_t maxValue = digits == 4 ? 9999u : 999u;
    magnitude = (std::min)(magnitude, maxValue);
    for (int i = digits - 1; i >= 0; --i) {
        const int digit = valid ? static_cast<int>(magnitude % 10u) : -2;
        magnitude /= 10u;
        Digit(context, target, x + i*kStep, y, digit, kWidth, kHeight, maxWidth, maxHeight, color);
    }
}

// Draw a thin line with small axis-aligned segments, without additional GPU shaders.
inline void Stroke(ID3D11DeviceContext1* context, ID3D11RenderTargetView* target,
                   float ax, float ay, float bx, float by, int width, int height,
                   const float (&color)[4], int thickness = 2) {
    const float length = std::hypot(bx - ax, by - ay);
    const int steps = (std::max)(1, static_cast<int>(length / 2.0f));
    for (int i = 0; i <= steps; ++i) {
        const float t = static_cast<float>(i) / steps;
        const int x = static_cast<int>(std::lround(ax + (bx - ax) * t));
        const int y = static_cast<int>(std::lround(ay + (by - ay) * t));
        Rect(context, target, x - thickness / 2, y - thickness / 2,
             thickness, thickness, width, height, color);
    }
}

inline void DrawHud(ID3D11DeviceContext1* context, ID3D11RenderTargetView* target,
                    int width, int height) {
    static LocalReceiver receiver;
    const LiveData data = receiver.poll();
    constexpr float transparent[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    constexpr float cyan[4] = {0.13f, 0.95f, 0.78f, 0.92f};
    constexpr float dim[4] = {0.07f, 0.65f, 0.55f, 0.78f};
    constexpr float warning[4] = {0.97f, 0.75f, 0.20f, 0.88f};
    context->ClearRenderTargetView(target, transparent);

    const int cx = width / 2;
    const int cy = height / 2;

    // Compact outboard numeric readouts, leaving the center of the cockpit clear.
    // Source texture remains 512px; the physical XR quad is reduced separately.
    const int left = (std::max)(12, cx - 207);
    const int right = (std::min)(width - 119, cx + 110);
    const int top = (std::max)(18, cy - 127);
    const int bottom = (std::min)(height - 60, cy + 89);
    DrawNumber(context, target, left, top, data.speedKmh, 3, false, data.fresh, width, height, cyan);
    DrawNumber(context, target, right, top, data.altitudeM, 4, true, data.fresh, width, height, cyan);
    DrawNumber(context, target, left, bottom, data.fuelKg, 4, false, data.fresh, width, height, dim);
    DrawNumber(context, target, right + 16, bottom, data.normalGCentis, 3, true, data.fresh, width, height, cyan);
    Rect(context, target, right + 71, bottom + 33, 5, 5, width, height, cyan);

    // Short instrument brackets (unobtrusive labels substitute until font rendering is added).
    Stroke(context, target, left, top - 10, left + 58, top - 10, width, height, dim);
    Stroke(context, target, right, top - 10, right + 58, top - 10, width, height, dim);
    Stroke(context, target, left, bottom + 48, left + 58, bottom + 48, width, height, dim);
    Stroke(context, target, right, bottom + 48, right + 58, bottom + 48, width, height, dim);

    // Fixed aircraft reference: center gap for the actual view through the visor.
    Stroke(context, target, cx - 46, cy, cx - 14, cy, width, height, cyan, 2);
    Stroke(context, target, cx + 14, cy, cx + 46, cy, width, height, cyan, 2);
    Stroke(context, target, cx, cy - 8, cx, cy + 8, width, height, cyan, 2);
    Stroke(context, target, cx - 14, cy + 11, cx - 7, cy + 17, width, height, dim, 2);
    Stroke(context, target, cx + 7, cy + 17, cx + 14, cy + 11, width, height, dim, 2);

    // Attitude horizon (pitch + bank). Missing orientation is never fabricated.
    if (data.fresh && data.pitchCentideg != kMissing && data.bankCentideg != kMissing) {
        // Flight telemetry arrives near 5 Hz, while VR frames are much faster.
        // Exponential, frame-time-based smoothing prevents 200 ms attitude steps.
        // Keep state across DrawHud() calls but reset after stale telemetry.
        struct SmoothedAttitude {
            bool initialized{false};
            float pitchDeg{0.0f};
            float bankRad{0.0f};
            std::chrono::steady_clock::time_point lastFrame{};
        };
        static SmoothedAttitude smooth{};
        const float targetPitchDeg = static_cast<float>(data.pitchCentideg) / 100.0f;
        const float targetBankRad = static_cast<float>(data.bankCentideg) * (3.1415926535f / 18000.0f);
        const auto now = std::chrono::steady_clock::now();
        if (!smooth.initialized) {
            smooth.pitchDeg = targetPitchDeg;
            smooth.bankRad = targetBankRad;
            smooth.initialized = true;
        } else {
            const float dt = std::chrono::duration<float>(now - smooth.lastFrame).count();
            // Filter only within sensible VR frame intervals; reset after long pauses.
            if (!(dt > 0.0f && dt < 0.5f)) {
                smooth.pitchDeg = targetPitchDeg;
                smooth.bankRad = targetBankRad;
            } else {
                constexpr float kTimeConstantSeconds = 0.13f;
                const float alpha = 1.0f - std::exp(-dt / kTimeConstantSeconds);
                smooth.pitchDeg += alpha * (targetPitchDeg - smooth.pitchDeg);
                // Wrap shortest angular path across +/-180 deg.
                const float delta = std::remainder(targetBankRad - smooth.bankRad, 6.283185307f);
                smooth.bankRad += alpha * delta;
            }
        }
        smooth.lastFrame = now;
        const float offset = (std::max)(-52.0f, (std::min)(52.0f, smooth.pitchDeg * 2.2f));
        // SCAF bank cue convention: line tilts toward the aircraft bank (user-tested direction).
        // This is a bank cue, not a geographically stabilized artificial horizon.
        const float sine = std::sin(smooth.bankRad);
        const float cosine = std::cos(smooth.bankRad);
        const float centerY = static_cast<float>(cy) + offset;
        const float radius = 64.0f;
        const float gap = 17.0f;
        const float vx = cosine, vy = sine;
        // Open center around the fixed aircraft reference symbol.
        Stroke(context, target, cx - radius*vx, centerY - radius*vy,
               cx - gap*vx, centerY - gap*vy, width, height, dim, 2);
        Stroke(context, target, cx + gap*vx, centerY + gap*vy,
               cx + radius*vx, centerY + radius*vy, width, height, dim, 2);
        // Upward tick in the rotated frame.
        Stroke(context, target, cx + radius*vx, centerY + radius*vy,
               cx + radius*vx - 7*vy, centerY + radius*vy + 7*vx, width, height, dim, 2);
    } else {
        // Amber markers indicate attitude unavailable; no fake level horizon.
        Stroke(context, target, cx - 55, cy + 42, cx - 28, cy + 42, width, height, warning, 2);
        Stroke(context, target, cx + 28, cy + 42, cx + 55, cy + 42, width, height, warning, 2);
    }
}

} // namespace scaf
