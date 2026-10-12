-- Nova Hub loader: works in every game. It looks up the game you're in and
-- runs that game's script; unsupported games get a short message instead.

local BASE = "https://raw.githubusercontent.com/Jaidendor/NovaHub-Loader/main/Games/"

-- game.GameId -> script. Add a line here for every new game.
local GAMES = {
    [9965411707] = { name = "Noob Incremental", file = "NoobIncremental.lua" },
}

local function notify(text)
    pcall(function()
        game:GetService("StarterGui"):SetCore("SendNotification", {
            Title = "Nova Hub",
            Text = text,
            Duration = 8,
        })
    end)
end

local entry = GAMES[game.GameId]
if not entry then
    print(string.format("[Nova Hub] this game isn't supported yet (GameId %d, PlaceId %d)", game.GameId, game.PlaceId))
    notify("This game isn't supported yet. Its ID is in the F9 console.")
    return
end

print("[Nova Hub] loading " .. entry.name .. "...")
local ok, source = pcall(function()
    return game:HttpGet(BASE .. entry.file)
end)
if not ok or type(source) ~= "string" or source == "" then
    warn("[Nova Hub] couldn't download the script for " .. entry.name .. ": " .. tostring(source))
    notify("Couldn't download the " .. entry.name .. " script. Try again in a moment.")
    return
end

local run, err = loadstring(source)
if not run then
    warn("[Nova Hub] the " .. entry.name .. " script didn't load: " .. tostring(err))
    notify("The " .. entry.name .. " script didn't load. Check the F9 console.")
    return
end
run()
