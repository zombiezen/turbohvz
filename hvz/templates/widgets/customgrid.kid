<table xmlns="http://www.w3.org/1999/xhtml"
     xmlns:py="http://purl.org/kid/ns#"
     class="${grid_class}" id="${name}">
    <thead>
        <th py:for="col in columns">
            <span py:if="sortable and col not in exclude_sorting" py:strip="">
            <?python
            if tg.paginate.order == col:
                reverse_link = not tg.paginate.reversed
                if tg.paginate.reversed:
                    header_class = 'descending'
                else:
                    header_class = 'ascending'
            else:
                reverse_link = False
                header_class = None
            ?>
            <a href="${tg.paginate.get_href(1, col, reverse_link)}" py:content="get_column_title(col)" class="${header_class}">[title]</a>
            </span>
            <span py:if="not sortable or col in exclude_sorting" py:replace="get_column_title(col)">[title]</span>
        </th>
    </thead>
    <tbody>
        <tr py:if="no_data_msg is not None and not value" class="no_data"><td colspan="${len(columns)}" py:content="no_data_msg">No data</td></tr>
        <tr py:for="i, row in enumerate(value)" class="${i % 2 and 'odd' or 'even'}">
            <td py:for="col in columns" class="${col}_column" py:content="get_cell(row, col)">[value]</td>
        </tr>
    </tbody>
</table>
