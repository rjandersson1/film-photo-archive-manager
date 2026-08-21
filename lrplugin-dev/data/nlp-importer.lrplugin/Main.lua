local LrTasks = import "LrTasks"
local Importer = require "Importer"

LrTasks.startAsyncTask(function()
    Importer.run()
end)