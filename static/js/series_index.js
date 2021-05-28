function addSubelement(elem, type, opts) {
    var new_elem = $("<" + type + ">", opts);
    elem.append(new_elem);

    return new_elem;
}

function SeriesEntry(series) {
    var root = $("<li>", { "class": "series-entry" });
    this.root = root;
    this.series = series;

    this.link = addSubelement(root, "a", { "class": "series-link", "href": series.url, "text": series.title });

    this.display_name = addSubelement(root, "span", {
        "class": "series-display-name",
        "text": " by " + series.author.display_name
    });

    this.username = addSubelement(root, "span", {
        "class": "series-username",
        "text": " (" + series.author.username + "#" + series.author.discriminator + ")"
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

        this.lastUpdated = addSubelement(this.root, "span", {
            "class": "series-update-time text-muted", "text": " — Last updated " + format_str
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

    this.entries = seriesList.map(function (series) {
        return new SeriesEntry(series);
    });

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

function compareByAuthor(elemA, elemB) {
    if (elemA.author.display_name < elemB.author.display_name) {
        return -1;
    } else if (elemA.author.display_name > elemB.author.display_name) {
        return 1;
    } else {
        if (elemA.author.username < elemB.author.username) {
            return -1;
        } else if (elemA.author.username > elemB.author.username) {
            return 1;
        } else {
            if (elemA.author.discriminator < elemB.author.discriminator) {
                return -1;
            } else if (elemA.author.discriminator > elemB.author.discriminator) {
                return 1;
            } else {
                return 0;
            }
        }
    }
}

function renderIndex(seriesData, byAuthor) {
    /* Sort by title */
    seriesData.sort(byAuthor ? compareByAuthor : compareByTitle);

    /* Construct index */
    var index = {};
    for (let series of seriesData) {
        let key = "";
        if (byAuthor) {
            key = series.author.display_name;
        } else {
            key = series.title[0].toUpperCase();
        }

        if (!index[key]) {
            index[key] = [];
        }

        index[key].push(series);
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
