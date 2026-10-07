--[[
    Gran Turismo UI App Settings Management Subsystem
    Manages user preferences (Audio effects, volumes)
    and persists them to settings/settings.ini.
]]

local Settings = {}
local instance = nil

local function getIniPath()
    local appFolder = (ac and ac.getFolder and ac.getFolder(ac.FolderID.ACApps)) or "apps"
    return appFolder .. "/lua/gt_license/settings/settings.ini"
end

local function getDefaultIniPath()
    local appFolder = (ac and ac.getFolder and ac.getFolder(ac.FolderID.ACApps)) or "apps"
    return appFolder .. "/lua/gt_license/settings/default_settings.ini"
end

local function loadConfig()
    local path = getIniPath()
    local ini = (ac and ac.INIConfig and ac.INIConfig.load(path)) or nil
    if not ini and ac and ac.INIConfig then
        ini = ac.INIConfig.load(getDefaultIniPath())
    end
    return ini
end

function Settings.new()
    local self = setmetatable({}, { __index = Settings })
    self:reload()
    return self
end

function Settings:reload()
    self.ini = loadConfig()
    local ini = self.ini

    if ini and ini.get then
        self.soundMaster    = ini:get("SOUND", "MASTER", true)
        self.soundCountdown = ini:get("SOUND", "COUNTDOWN", true)
        self.soundBuzzer    = ini:get("SOUND", "BUZZER", true)
        self.soundFanfare   = ini:get("SOUND", "FANFARE", true)
        self.soundVolume    = ini:get("SOUND", "VOLUME", 0.8)
    else
        self.soundMaster    = true
        self.soundCountdown = true
        self.soundBuzzer    = true
        self.soundFanfare   = true
        self.soundVolume    = 0.8
    end
end

function Settings:update(section, key, value)
    if self.ini and self.ini.set then
        self.ini:set(section, key, value)
        if self.ini.save then
            self.ini:save(getIniPath())
        end
    end
    self:reload()
end

function Settings.get()
    if not instance then
        instance = Settings.new()
    end
    return instance
end

return Settings
