<table xmlns="http://www.w3.org/1999/xhtml"
     xmlns:py="http://purl.org/kid/ns#"
     class="${grid_class}" id="${name}">
    <thead>
        <th py:for="col in columns" py:content="get_column_title(col)">[title]</th>
    </thead>
    <tr py:for="i, row in enumerate(value)" class="${i % 2 and 'odd' or 'even'}">
        <td py:for="col in columns" class="${col}_column" py:content="get_cell(row, col)">[value]</td>
    </tr>
</table>
