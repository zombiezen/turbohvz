//
//  fieldlist.js
//  TurboHvZ
//
//  Created by Ross Light on April 27, 2008.
//  Copyright (C) 2008 Ross Light.
//

function fieldlist_add_row(field_name, event)
{
    var widget_elem = event.src().parentNode;
    var list_elem = getElementsByTagAndClassName('ul', null, widget_elem)[0];
    var new_field = INPUT({'type': 'text', 'name': field_name});
    var delete_link = A({'href': '#'}, 'Delete');
    var list_item = LI(null, new_field, ' ', delete_link);
    appendChildNodes(list_elem, list_item);
    connect(delete_link, 'onclick', fieldlist_delete_row);
    event.stop();
}

function fieldlist_delete_row(event)
{
    var list_item = event.src().parentNode;
    var list_elem = list_item.parentNode;
    var all_list_items = getElementsByTagAndClassName('li', null, list_elem);
    if (all_list_items.length > 1)
    {
        removeElement(list_item);
    }
    else
    {
        alert("You cannot delete the last row.");
    }
    event.stop();
}

function fieldlist_connect_deletes(field)
{
    var field_elem = getElement(field);
    var list_elem = getElementsByTagAndClassName('ul', null, field_elem)[0];
    var list_items = getElementsByTagAndClassName('li', null, list_elem);
    forEach(list_items, function(list_item)
    {
        var del_link = getElementsByTagAndClassName('a', null, list_item)[0];
        connect(del_link, 'onclick', fieldlist_delete_row);
    });
}
