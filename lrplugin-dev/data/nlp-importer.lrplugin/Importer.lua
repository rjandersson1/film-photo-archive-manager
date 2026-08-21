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

    -- Detects NLP's "-positive.tif" (or "-positive-2.tif" etc. -- NLP can
    -- generate more than one positive per raw capture) companions that
    -- haven't been renamed to "_positive.tif" yet. "-" sorts before "." in
    -- any filename-sorted view (eg. Quick Collection sorted by filename),
    -- so an unrenamed file like this appears BEFORE its own master's
    -- ".ARW" filename on screen -- breaking syncVCs.py's assumption that
    -- the master is always visually first in its stack. Renaming to
    -- "_positive.tif"/"_positive-2.tif" (underscore sorts after ".") fixes
    -- this at the source; this just flags any still needing it, matched
    -- case-insensitively via a lowered path.
    local function isUnrenamedPositiveTiff(path)
        if not path then return false end
        local lowered = path:lower()
        return lowered:match("%-positive%-?%d*%.tiff?$") ~= nil
    end

    -- Writes an ordered manifest for syncVCs.py -- for each on-screen stack
    -- top (stackPositionInFolder == 1, or nil if not stacked at all), how
    -- many more Shift+Right presses would select every other member of
    -- that stack. Uses Lightroom's own stack structure directly
    -- (stackPositionInFolder / countStackInFolderMembers, both documented
    -- getRawMetadata keys) rather than our JSON-derived VC/companion
    -- matching -- this reflects on-screen grouping regardless of whether a
    -- member is a true virtual copy or a real stacked file like
    -- "-positive.tif", which is exactly what on-screen navigation needs.
    local manifestPath = "/Users/rja/Documents/Coding/film-photo-archive-manager/lrplugin-dev/vc_manifest.txt"
    local manifestFile, manifestErr = io.open(manifestPath, "w")

    if manifestFile then
        -- WARNING lines first -- syncVCs.py's rename pre-pass reads these
        -- (and the sync pass refuses to run at all while any exist).
        -- Position is 0-based, on-screen offset from the FIRST photo in
        -- selectedPhotos -- how many plain Right-arrow presses from the
        -- start land on this exact photo, so the rename pre-pass can find
        -- it without any "select by filename" capability.
        for idx, p in ipairs(selectedPhotos) do
            local path = p:getRawMetadata("path")
            if isUnrenamedPositiveTiff(path) then
                local fname = p:getFormattedMetadata("fileName") or path
                manifestFile:write("WARNING\t" .. fname .. "\t" .. tostring(idx - 1) .. "\n")
            end
        end

        for _, p in ipairs(selectedPhotos) do
            local pos = p:getRawMetadata("stackPositionInFolder")
            if pos == nil or pos == 1 then
                -- countStackInFolderMembers returns 0 (not nil) for a photo
                -- that isn't stacked at all -- "0 or 1" never fires here
                -- since 0 is truthy in Lua (only nil/false are falsy), so
                -- this used to compute 0 - 1 = -1 for every unstacked photo.
                -- Confirmed against real data: DSC00008 (5 known VCs)
                -- computed correctly as 5, proving the formula itself is
                -- right for genuinely stacked photos -- only the "not
                -- stacked at all" case was wrong. Clamping to a 0 floor
                -- fixes both nil and explicit-0 identically.
                local total = p:getRawMetadata("countStackInFolderMembers") or 0
                local copyCount = math.max(total - 1, 0)
                local fname = p:getFormattedMetadata("fileName") or ""
                manifestFile:write(fname .. "\t" .. tostring(copyCount) .. "\n")
            end
        end
        manifestFile:close()
    end

    LrDialogs.message(
        "Import complete",
        "Matched: " .. tostring(matched) .. "\nVirtual copies synced: " .. tostring(vcSynced) .. "\nStack companions synced: " .. tostring(stackSynced) .. "\nUnmatched: " .. tostring(missing)
            .. (manifestFile == nil and manifestErr and ("\n\nWARNING: vc_manifest.txt write failed:\n" .. tostring(manifestErr)) or ""),
        "info"
    )

end

return Importer