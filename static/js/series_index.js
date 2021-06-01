function addSubelement(elem, type, opts) {
    var new_elem = $("<" + type + ">", opts);
    elem.append(new_elem);

    return new_elem;
}

function AuthorDisplay(author) {
    this.root = $("<span>", { "class": "author-container" });

    this.display_name = addSubelement(this.root, "span", {
        "class": "author-display-name",
        "text": author.display_name
    });

    this.usernameContainer = addSubelement(this.root, "span", {
        "class": "author-username-container"
    });

    this.username = addSubelement(this.usernameContainer, "span", {
        "class": "author-username",
        "text": author.username
    });

    this.discriminator = addSubelement(this.usernameContainer, "span", {
        "class": "author-discriminator",
        "text": author.discriminator
    });
}

function SeriesEntry(series) {
    this.root = $("<li>", { "class": "series-entry" });
    this.series = series;

    this.titleBar = addSubelement(this.root, "div", { "class": "series-titlebar" });
    this.infoBar = addSubelement(this.root, "div", { "class": "series-infobar" });

    this.link = addSubelement(this.titleBar, "a", { "class": "series-link", "href": series.url, "text": series.title });

    this.authorContainer = addSubelement(this.titleBar, "span", { "class": "series-authors" });
    this.authorDisplays = series.authors.map((author) => new AuthorDisplay(author));

    this.authorContainer.append("by ");

    for (let i = 0; i < this.authorDisplays.length; i++) {
        if (this.authorDisplays.length > 1 && i > 0) {
            this.authorContainer.append(
                (this.authorDisplays.length > 2 ? ", " : " ")
                + (i === this.authorDisplays.length - 1 ? "and " : "")
            );
        }

        this.authorContainer.append(this.authorDisplays[i].root);
    }

    addSubelement(this.infoBar, "span", {
        "class": "series-part-count",
        "text": series.n_snippets.toString() + " parts"
    });

    addSubelement(this.infoBar, "span", {
        "class": "series-word-count",
        "text": series.wordcount.toString() + " words"
    });

    if (series.updated) {
        var series_updated = new Date(Math.round(series.updated * 1000));
        var now = new Date();

        var elapsed_time = now.getTime() - series_updated.getTime();

        var format_str = '';
        if (elapsed_time < 5 * 60 * 1000) {
            // <5 minutes ago - display 'just now'
            format_str = 'just now';
        } else if (elapsed_time < 60 * 60 * 1000) {
            // < 1 hour ago - display minutes since last update
            format_str = Math.floor(elapsed_time / (60 * 1000)) + ' minutes ago';
        } else if (elapsed_time < 24 * 60 * 60 * 1000) {
            // < 1 day ago - display hours since last update
            var n_hours = Math.floor(elapsed_time / (60 * 60 * 1000));
            format_str = n_hours + (n_hours === 1 ? ' hour ago' : ' hours ago');
        } else {
            // otherwise just display days since last update
            var n_days = Math.floor(elapsed_time / (24 * 60 * 60 * 1000));
            format_str = n_days + (n_days === 1 ? ' day ago' : ' days ago');
        }

        this.lastUpdated = addSubelement(this.infoBar, "span", {
            "class": "series-update-time", "text": "Last updated " + format_str
        });
    } else {
        this.lastUpdated = null;
    }
}


function SeriesList(key, seriesList, authorHeader) {
    this.key = key;
    this.seriesList = seriesList;
    this.root = $("<div>", { "class": "series-list-container" });

    this.id = (authorHeader ? "author" : "title") + "-index-" + key;
    this.header = addSubelement(this.root, "h2", {
        "class": "series-list-header",
        "id": this.id,
        "text": this.key
    });


    this.list = addSubelement(this.root, "ul", { "class": "series-list" });
    this.entries = seriesList.map((series) => new SeriesEntry(series));

    for (var entry of this.entries) {
        this.list.append(entry.root);
    }

    this.navItem = $("<li>", { "class": "nav-item index-nav-item" });
    addSubelement(this.navItem, "a", { "class": "nav-link", "href": "#" + this.id, "text": this.key });
}

function compareByTitle(elemA, elemB) {
    if (elemA.title < elemB.title) {
        return -1;
    } else if (elemA.title > elemB.title) {
        return 1;
    } else {
        return 0;
    }
}

function compareArrays(a, b, compareFunc) {
    var maxIndex = a.length > b.length ? a.length : b.length;

    for (let i = 0; i < maxIndex; i++) {
        if (i >= a.length) {
            return -1;
        } else if (i >= b.length) {
            return 1;
        } else {
            let r = compareFunc(a[i], b[i]);
            if (r != 0) {
                return r;
            }
        }
    }

    return 0;
}

function compareByAuthors(elemA, elemB) {
    return compareArrays(elemA.authors, elemB.authors, (authorA, authorB) => compareArrays(
        [authorA.display_name, authorA.username, authorA.discriminator],
        [authorB.display_name, authorB.username, authorB.discriminator],
        (a, b) => (a > b ? 1 : (a < b ? -1 : 0))
    ));
}

function renderIndex(seriesData, byAuthor) {
    /* Sort by title */
    seriesData.sort(byAuthor ? compareByAuthors : compareByTitle);

    /* Construct index */
    var index = {};
    for (let series of seriesData) {
        let keys = [];
        if (byAuthor) {
            for (let author of series.authors) {
                keys.push(author.display_name + " (" + author.username + "#" + author.discriminator + ")");
            }
        } else {
            keys.push(series.title[0].toUpperCase());
        }

        for (let key of keys) {
            if (!index[key]) {
                index[key] = [];
            }

            index[key].push(series);
        }
    }

    var indexElems = [];
    for (let key of Object.keys(index)) {
        indexElems.push(new SeriesList(key, index[key], byAuthor));
    }

    indexElems.sort((elemA, elemB) => {
        if (elemA.header < elemB.header) {
            return -1;
        } else if (elemA.header > elemB.header) {
            return 1;
        } else {
            return 0;
        }
    });

    var indexContainer = $(byAuthor ? "#author-index" : "#title-index");
    var headerNav = $(byAuthor ? "#author-index-nav" : "#title-index-nav");
    for (let elem of indexElems) {
        indexContainer.append(elem.root);
        headerNav.append(elem.navItem);
    }
}

function navigateTab(showAuthorIndex) {
    var activeTab = $(showAuthorIndex ? "#author-index-tab" : "#title-index-tab");
    var inactiveTab = $(showAuthorIndex ? "#title-index-tab" : "#author-index-tab");
    var activePane = $(showAuthorIndex ? "#author-index-container" : "#title-index-container");
    var inactivePane = $(showAuthorIndex ? "#title-index-container" : "#author-index-container");

    activeTab.addClass("active");
    inactiveTab.removeClass("active");

    activePane.show();
    inactivePane.hide();
}

$(function () {
    $("#author-index-container").hide();

    $("#title-index-tab").click(function () {
        navigateTab(false);
    });

    $("#author-index-tab").click(function () {
        navigateTab(true);
    });

    fetch("/api/series").then(function (response) {
        return response.json();
    }).then(function (seriesData) {
        renderIndex(seriesData, false);
        renderIndex(seriesData, true);
    });
});
