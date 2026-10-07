--[[
    Gran Turismo License HUD - Assetto Corsa Lua UI App Entry Point
    Loads screen handlers, initializes shared state connection, and
    registers window callbacks for Assetto Corsa's native App system.
]]

require("screens/theme")
require("screens/settings")
require("screens/shared_state")

require("screens/timer_screen")
require("screens/ghost_screen")
require("screens/config_screen")
