local LrTasks = import "LrTasks"
local Importer = require "Importer"

LrTasks.startAsyncTask(function()
    Importer.exportSelection()
end)
