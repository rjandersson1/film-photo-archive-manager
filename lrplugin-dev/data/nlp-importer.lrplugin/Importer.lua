local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrFileUtils = import "LrFileUtils"

local json = require "json"

local Importer = {}

local function readFile(path)

    local f = io.open(path, "rb")
    if not f then
        error("Could not open JSON file: " .. tostring(path))
    end

    local content = f:read("*all")
    f:close()

    return content
end


local function chooseJsonFile()

    local result = LrDialogs.runOpenPanel({
        title = "Select JSON metadata file",
        canChooseFiles = true,
        canChooseDirectories = false,
        allowsMultipleSelection = false,
        fileTypes = { "json" },
    })

    if not result or #result == 0 then
        return nil
    end

    return result[1]
end


local function buildPhotoIndex(photos)

    local index = {}

    for _, photo in ipairs(photos) do

        local fileName = photo:getFormattedMetadata("fileName")

        if fileName then
            index[string.lower(fileName)] = photo
        end

    end

    return index
end


local function applyMetadata(photo, record)

    if record.standard then
        for key, value in pairs(record.standard) do
            if value ~= nil and value ~= "" then
                photo:setRawMetadata(key, value)
            end
        end
    end

    if record.title ~= nil then
        photo:setRawMetadata("title", record.title)
    end

    if record.caption ~= nil then
        photo:setRawMetadata("caption", record.caption)
    end

    if record.rating ~= nil then
        photo:setRawMetadata("rating", tonumber(record.rating))
    end

end


-- Builds a path -> {VC photos} index in ONE pass over the whole catalog,
-- instead of re-scanning it for every matched master. The previous version
-- called getRawMetadata() on every catalog photo for EVERY matched master
-- (O(masters x catalog size)) -- as the catalog has grown across rolls, that
-- got dramatically slower. This is O(catalog size) total, regardless of how
-- many masters are being processed.
local function buildVirtualCopyIndex(allPhotos)

    local index = {}

    for _, photo in ipairs(allPhotos) do
        if photo:getRawMetadata("isVirtualCopy") then
            local path = photo:getRawMetadata("path")
            if path then
                if not index[path] then
                    index[path] = {}
                end
                table.insert(index[path], photo)
            end
        end
    end

    return index

end


-- Looks up masterPhoto's virtual copies via the index above -- VCs share the
-- master's underlying file path (they don't have their own), so this is a
-- direct O(1) lookup rather than a scan.
local function getVirtualCopiesOf(masterPhoto, vcIndex)

    local masterPath = masterPhoto:getRawMetadata("path")

    if not masterPath then
        return {}
    end

    return vcIndex[masterPath] or {}

end


-- Real files stacked with masterPhoto (eg. NLP's "Create Positive .tiff +
-- Stack with Original" -- a genuinely separate TIFF file, not a virtual
-- copy: different path, isVirtualCopy = false) that have NO JSON record of
-- their own. "isInStackInFolder" / "stackInFolderMembers" are documented
-- getRawMetadata keys.
--
-- Only companions with no record of their own qualify -- list_raw_files()
-- (newRoll.py) already deliberately excludes "-positive.tif" derivatives
-- from ever getting their own xlsx row/JSON record, since they're not a
-- standalone exposure; that's exactly the case this is meant to catch. A
-- stack member that DOES have its own record is a genuinely independent
-- exposure someone stacked for comparison, and gets its own metadata from
-- its own match in the main loop -- never silently overwritten with the
-- master's values here.
local function getStackCompanionsOf(masterPhoto, recordFileNames)

    if not masterPhoto:getRawMetadata("isInStackInFolder") then
        return {}
    end

    local members = masterPhoto:getRawMetadata("stackInFolderMembers") or {}
    local companions = {}

    for _, member in ipairs(members) do
        if member ~= masterPhoto then
            local memberFileName = member:getFormattedMetadata("fileName")
            local hasOwnRecord = memberFileName and recordFileNames[string.lower(memberFileName)]
            if not hasOwnRecord then
                table.insert(companions, member)
            end
        end
    end

    return companions

end


function Importer.run()

    local catalog = LrApplication.activeCatalog()
    local selectedPhotos = catalog:getTargetPhotos()

    if not selectedPhotos or #selectedPhotos == 0 then
        LrDialogs.message("Select photos first.")
        return
    end

    -- local jsonPath = chooseJsonFile()
    local jsonPath = "/Users/rja/Documents/Coding/film-photo-archive-manager/lrplugin-dev/metadata.json"

    -- if not jsonPath then
    --     return
    -- end

    local content = readFile(jsonPath)

    local records = json.decode(content)

    if type(records) ~= "table" then
        error("JSON root must be an array.")
    end

    local photoIndex = buildPhotoIndex(selectedPhotos)
    local allPhotos = catalog:getAllPhotos()
    local vcIndex = buildVirtualCopyIndex(allPhotos)

    -- Which filenames already have their own JSON record -- used by
    -- getStackCompanionsOf() to tell a "-positive.tif"-style derivative
    -- (no record of its own, inherits the master's metadata) apart from a
    -- genuinely independent frame someone stacked for comparison (has its
    -- own record, gets its own metadata, never touched here).
    local recordFileNames = {}
    for _, record in ipairs(records) do
        if record.fileName then
            recordFileNames[string.lower(record.fileName)] = true
        end
    end

    local matched = 0
    local missing = 0
    local vcSynced = 0
    local stackSynced = 0

    catalog:withWriteAccessDo("Import JSON metadata", function()

        for _, record in ipairs(records) do

            local fileName = record.fileName

            if fileName then

                local photo = photoIndex[string.lower(fileName)]

                if photo then
                    applyMetadata(photo, record)
                    matched = matched + 1

                    for _, vc in ipairs(getVirtualCopiesOf(photo, vcIndex)) do
                        applyMetadata(vc, record)
                        vcSynced = vcSynced + 1
                    end

                    for _, companion in ipairs(getStackCompanionsOf(photo, recordFileNames)) do
                        applyMetadata(companion, record)
                        stackSynced = stackSynced + 1
                    end
                else
                    missing = missing + 1
                end

            else
                missing = missing + 1
            end

        end

    end)

    LrDialogs.message(
        "Import complete",
        "Matched: " .. tostring(matched) .. "\nVirtual copies synced: " .. tostring(vcSynced) .. "\nStack companions synced: " .. tostring(stackSynced) .. "\nUnmatched: " .. tostring(missing),
        "info"
    )

end

return Importer