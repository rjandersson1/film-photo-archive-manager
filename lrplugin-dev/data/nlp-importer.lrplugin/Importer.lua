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


-- Finds masterPhoto's virtual copies: any other photo in the same folder
-- whose file path matches masterPhoto's exactly (VCs share the master's
-- underlying file -- they don't have their own path) and that is flagged
-- isVirtualCopy. Scoped to the master's own folder rather than the whole
-- catalog -- a VC always lives in the same folder as its master, and this
-- keeps the scan small regardless of catalog size.
local function getVirtualCopiesOf(masterPhoto)

    local masterPath = masterPhoto:getRawMetadata("path")
    local folder = masterPhoto:getRawMetadata("folder")

    if not masterPath or not folder then
        return {}
    end

    local copies = {}

    for _, candidate in ipairs(folder:getPhotos()) do
        if candidate ~= masterPhoto
            and candidate:getRawMetadata("path") == masterPath
            and candidate:getRawMetadata("isVirtualCopy") then
            table.insert(copies, candidate)
        end
    end

    return copies

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

    local matched = 0
    local missing = 0
    local vcSynced = 0

    catalog:withWriteAccessDo("Import JSON metadata", function()

        for _, record in ipairs(records) do

            local fileName = record.fileName

            if fileName then

                local photo = photoIndex[string.lower(fileName)]

                if photo then
                    applyMetadata(photo, record)
                    matched = matched + 1

                    for _, vc in ipairs(getVirtualCopiesOf(photo)) do
                        applyMetadata(vc, record)
                        vcSynced = vcSynced + 1
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
        "Matched: " .. tostring(matched) .. "\nVirtual copies synced: " .. tostring(vcSynced) .. "\nUnmatched: " .. tostring(missing),
        "info"
    )

end

return Importer