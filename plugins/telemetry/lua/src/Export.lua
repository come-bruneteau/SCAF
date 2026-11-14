
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

function LuaExportAfterNextFrame()
    if not udp then
        return
    end

    local time = LoGetModelTime()

    if not time then
        return
    end

    if last_send < 0 or time < last_send
        or time - last_send >= 1.0 then

        last_send = time

        local message = string.format(
            "SCAF_HELLO,%.2f",
            time
        )

        udp:send(message)
    end
end

function LuaExportStop()
    if udp then
        udp:close()
        udp = nil
    end
end
