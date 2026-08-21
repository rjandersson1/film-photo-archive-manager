local json = {}

local function skipWhitespace(str, i)
    while true do
        local c = str:sub(i, i)
        if c == " " or c == "\n" or c == "\r" or c == "\t" then
            i = i + 1
        else
            break
        end
    end
    return i
end

local function parseString(str, i)
    i = i + 1
    local result = {}

    while i <= #str do
        local c = str:sub(i, i)

        if c == '"' then
            return table.concat(result), i + 1
        elseif c == "\\" then
            local n = str:sub(i + 1, i + 1)

            if n == '"' or n == "\\" or n == "/" then
                result[#result + 1] = n
                i = i + 2
            elseif n == "b" then
                result[#result + 1] = "\b"
                i = i + 2
            elseif n == "f" then
                result[#result + 1] = "\f"
                i = i + 2
            elseif n == "n" then
                result[#result + 1] = "\n"
                i = i + 2
            elseif n == "r" then
                result[#result + 1] = "\r"
                i = i + 2
            elseif n == "t" then
                result[#result + 1] = "\t"
                i = i + 2
            else
                error("Invalid escape sequence at position " .. tostring(i))
            end
        else
            result[#result + 1] = c
            i = i + 1
        end
    end

    error("Unterminated string")
end

local function parseNumber(str, i)
    local startI = i
    local c = str:sub(i, i)

    if c == "-" then
        i = i + 1
    end

    while str:sub(i, i):match("%d") do
        i = i + 1
    end

    if str:sub(i, i) == "." then
        i = i + 1
        while str:sub(i, i):match("%d") do
            i = i + 1
        end
    end

    local e = str:sub(i, i)
    if e == "e" or e == "E" then
        i = i + 1
        local sign = str:sub(i, i)
        if sign == "+" or sign == "-" then
            i = i + 1
        end
        while str:sub(i, i):match("%d") do
            i = i + 1
        end
    end

    local numStr = str:sub(startI, i - 1)
    local num = tonumber(numStr)

    if num == nil then
        error("Invalid number: " .. numStr)
    end

    return num, i
end

local parseValue

local function parseArray(str, i)
    local arr = {}
    i = i + 1
    i = skipWhitespace(str, i)

    if str:sub(i, i) == "]" then
        return arr, i + 1
    end

    while true do
        local value
        value, i = parseValue(str, i)
        arr[#arr + 1] = value

        i = skipWhitespace(str, i)
        local c = str:sub(i, i)

        if c == "]" then
            return arr, i + 1
        elseif c == "," then
            i = i + 1
            i = skipWhitespace(str, i)
        else
            error("Expected ',' or ']' at position " .. tostring(i))
        end
    end
end

local function parseObject(str, i)
    local obj = {}
    i = i + 1
    i = skipWhitespace(str, i)

    if str:sub(i, i) == "}" then
        return obj, i + 1
    end

    while true do
        local key

        if str:sub(i, i) ~= '"' then
            error("Expected string key at position " .. tostring(i))
        end

        key, i = parseString(str, i)
        i = skipWhitespace(str, i)

        if str:sub(i, i) ~= ":" then
            error("Expected ':' at position " .. tostring(i))
        end

        i = i + 1
        i = skipWhitespace(str, i)

        local value
        value, i = parseValue(str, i)
        obj[key] = value

        i = skipWhitespace(str, i)
        local c = str:sub(i, i)

        if c == "}" then
            return obj, i + 1
        elseif c == "," then
            i = i + 1
            i = skipWhitespace(str, i)
        else
            error("Expected ',' or '}' at position " .. tostring(i))
        end
    end
end

parseValue = function(str, i)
    i = skipWhitespace(str, i)
    local c = str:sub(i, i)

    if c == '"' then
        return parseString(str, i)
    elseif c == "{" then
        return parseObject(str, i)
    elseif c == "[" then
        return parseArray(str, i)
    elseif c == "-" or c:match("%d") then
        return parseNumber(str, i)
    elseif str:sub(i, i + 3) == "true" then
        return true, i + 4
    elseif str:sub(i, i + 4) == "false" then
        return false, i + 5
    elseif str:sub(i, i + 3) == "null" then
        return nil, i + 4
    else
        error("Unexpected token at position " .. tostring(i))
    end
end

function json.decode(str)
    local result, i = parseValue(str, 1)
    i = skipWhitespace(str, i)

    if i <= #str then
        error("Unexpected trailing data at position " .. tostring(i))
    end

    return result
end

return json