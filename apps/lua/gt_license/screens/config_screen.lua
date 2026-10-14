--[[
    Gran Turismo UI Configuration & Preferences Screen
    Handles script.configHUD(dt) callback for the settings window.
]]

local Settings = require("screens/settings")

function script.configHUD(dt)
    local cfg = Settings.get()
    if not ui or not ui.tabBar then return end

    ui.tabBar("gtLicenseConfigTabs", function()
        -- Tab 1: Sound & Audio
        ui.tabItem("Audio", function()
            ui.newLine(4)
            if ui.checkbox("Master Audio Effects", cfg.soundMaster) then
                cfg:update("SOUND", "MASTER", not cfg.soundMaster)
            end

            local vol, volChanged = ui.slider("Audio Volume", cfg.soundVolume or 0.8, 0.0, 1.0, "%.0f%%")
            if volChanged then
                cfg:update("SOUND", "VOLUME", vol)
            end

            ui.newLine(6)
            if ui.checkbox("Countdown Beeps (3-2-1-GO)", cfg.soundCountdown) then
                cfg:update("SOUND", "COUNTDOWN", not cfg.soundCountdown)
            end

            if ui.checkbox("Failure Buzzer", cfg.soundBuzzer) then
                cfg:update("SOUND", "BUZZER", not cfg.soundBuzzer)
            end

            if ui.checkbox("Pass / Medal Fanfares", cfg.soundFanfare) then
                cfg:update("SOUND", "FANFARE", not cfg.soundFanfare)
            end
        end)

        -- Tab 2: Controls & Info
        ui.tabItem("Shortcuts", function()
            ui.newLine(4)
            ui.text("Driving School Shortcuts:")
            ui.bulletText("Press [ R ] to instantly restart test")
            ui.bulletText("Press [ ESC ] to open pause menu")
            ui.newLine(8)
            ui.text("HUD Widgets can be locked in place with their title bar pin/lock icon.")
            ui.text("HUD Widgets can be scaled individually using their bottom-right resize handle.")
            ui.newLine(8)
            ui.text("Assetto Corsa GT-Like Licenses v1.0.0")
            ui.text("By Nico Munoz & Community")
        end)
    end)
end

