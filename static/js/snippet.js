function loadSnippet(snippet_id) {
    var container = document.getElementById("snippet-" + snippet_id);
    container.innerHTML = "<i>Loading...</i>";

    fetch("/api/snippet/" + snippet_id).then(function (response) {
        return response.text();
    }).then(function (snippetContent) {
        container.innerHTML = discordMarkdown.toHTML(snippetContent);
    });
}