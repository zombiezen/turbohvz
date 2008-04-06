<div xmlns="http://www.w3.org/1999/xhtml"
     xmlns:py="http://purl.org/kid/ns#"
     class="pager" id="${name}">
    <p>Page <span class="current_num" py:content="tg.paginate.current_page">#</span> of <span class="page_count" py:content="tg.paginate.page_count">#</span></p>
    <p py:if="tg.paginate.page_count &gt; 1">
        <a href="${tg.paginate.get_href(1)}" py:strip="tg.paginate.current_page == 1">First</a>
        <span py:for="page in tg.paginate.pages" py:strip="">
            <span py:if="page == tg.paginate.current_page" class="current" py:content="page">#</span>
            <a py:if="page != tg.paginate.current_page" href="${tg.paginate.get_href(page)}" py:content="page">#</a>
        </span>
        <a href="${tg.paginate.get_href(tg.paginate.page_count)}" py:strip="tg.paginate.current_page == tg.paginate.page_count">Last</a>
    </p>
</div>
