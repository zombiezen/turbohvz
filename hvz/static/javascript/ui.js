//
//  ui.js
//  TurboHvZ
//
//  Created by Ross Light on April 15, 2008.
//  Copyright (C) 2008 Ross Light.
//

function safe_connect(src)
{
    // Fetch element
    if (typeof(src) == "string")
    {
        src = getElement(src);
    }
    // Connect if source is not null
    if (!isUndefinedOrNull(src))
    {
        connect.apply(null, arguments);
    }
}

function redirect(url)
{
    window.location = url;
}

function confirm_action(msg, url)
{
    if (confirm(msg))
    {
        redirect(url);
    }
}
