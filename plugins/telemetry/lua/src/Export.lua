
-- SCAF-DCS Telemetry Plugin
-- Initial UDP communication test
-- Need to be moved to user DCS Scripts folder

local HOST = "127.0.0.1"
local PORT = 50500

local udp = nil
local last_send = -1

function LuaExportStart()
    package.path = package.path
        .. ";.\\LuaSocket\\?.lua"

    package.cpath = package.cpath
        .. ";.\\LuaSocket\\?.dll"

    local ok, socket = pcall(require, "socket")

    if not ok then
        log.write(
            "SCAF",
            log.ERROR,
            "LuaSocket unavailable: " .. tostring(socket)
        )
        return
    end

    local client, err = socket.udp()

    if not client then
        log.write("SCAF", log.ERROR, tostring(err))
        return
    end

    client:settimeout(0)

    local connected, connect_err =
        client:setpeername(HOST, PORT)

    if not connected then
        log.write("SCAF", log.ERROR, tostring(connect_err))
        client:close()
        return
    end

    udp = client
    last_send = -1

    log.write("SCAF", log.INFO, "UDP initialized")
end

local sequence = 0

local function json_number(value)
    if type(value) ~= "number"
        or value ~= value
        or value == math.huge
        or value == -math.huge then
        return "null"
    end

    return string.format("%.6f", value)
end

local function json_string(value)
    value = tostring(value or "unknown")

    return '"' .. value:gsub('[%z\1-\31\\"]', function(c)
        local escapes = {
            ['\\'] = '\\\\',
            ['"'] = '\\"',
            ['\n'] = '\\n',
            ['\r'] = '\\r',
            ['\t'] = '\\t'
        }
        return escapes[c] or string.format("\\u%04x", string.byte(c))
    end) .. '"'
end

local function read_telemetry(time)
    local self_data = LoGetSelfData()
    if not self_data then
        return nil
    end

    local engine = LoGetEngineInfo()
    local acceleration = LoGetAccelerationUnits()
    local location = self_data.LatLongAlt or {}

    sequence = sequence + 1

    return string.format(
        '{"protocol":"scaf.telemetry",' ..
        '"version":1,' ..
        '"type":"aircraft.state",' ..
        '"sequence":%d,' ..
        '"timestamp":%s,' ..
        '"aircraft":{"type":%s},' ..
        '"data":{' ..
            '"speed_mps":%s,' ..
            '"altitude_m":%s,' ..
            '"fuel_internal_kg":%s,' ..
            '"fuel_external_kg":%s,' ..
            '"acceleration_g":{' ..
                '"x":%s,"y":%s,"z":%s' ..
            '},' ..
            '"position":{' ..
                '"lat_deg":%s,' ..
                '"lon_deg":%s,' ..
                '"alt_m":%s' ..
            '}' ..
        '}}',
        sequence,
        json_number(time),
        json_string(self_data.Name),
        json_number(LoGetIndicatedAirSpeed()),
        json_number(LoGetAltitudeAboveSeaLevel()),
        json_number(engine and engine.fuel_internal),
        json_number(engine and engine.fuel_external),
        json_number(acceleration and acceleration.x),
        json_number(acceleration and acceleration.y),
        json_number(acceleration and acceleration.z),
        json_number(location.Lat),
        json_number(location.Long),
        json_number(location.Alt)
    )
end

function LuaExportAfterNextFrame()
    if not udp then return end

    local time = LoGetModelTime()
    if not time then return end

    -- Reset after mission time restart.
    if last_send >= 0 and time < last_send then
        last_send = -1
        sequence = 0
    end

    -- Target acquisition frequency: 5 Hz.
    if last_send >= 0 and time - last_send < 0.2 then
        return
    end

    last_send = time

    local ok, message = pcall(read_telemetry, time)

    if not ok then
        log.write("SCAF", log.ERROR, tostring(message))
        return
    end

    if message then
        udp:send(message)
    end
end

function LuaExportStop()
    if udp then
        udp:close()
        udp = nil
    end
end
