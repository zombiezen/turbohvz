<div xmlns="http://www.w3.org/1999/xhtml"
     xmlns:py="http://purl.org/kid/ns#"
     id="${field_id}" class="${field_class}"
     py:attrs="attrs">
    <?python
        if (isinstance(value, basestring)):
            value = [value]
    ?>
    <ul>
        <li py:for="i, item in enumerate(value)">
            <input type="text" name="${name}" value="${item}" />
            <a href="#">Delete</a>
            <span py:if="isinstance(error, (list, tuple)) and i &lt; len(error)" class="fielderror" py:content="error[i]">[error]</span>
        </li>
        <li py:if="not value">
            <input type="text" name="${name}" />
            <a href="#">Delete</a>
        </li>
    </ul>
    <script type="text/javascript">
        fieldlist_connect_deletes(${tg.jsencode(field_id)});
    </script>
    <a id="${field_id}_add_link" href="#">Add Row</a>
    <script type="text/javascript">
        connect(${tg.jsencode(field_id)} + '_add_link', 'onclick',
                partial(fieldlist_add_row, ${tg.jsencode(name)}));
    </script>
</div>
