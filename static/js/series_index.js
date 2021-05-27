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
        "text": "by " + series.author.display_name
    });

    this.username = addSubelement(root, "span", {
        "class": "series-username",
        "text": series.author.username + "#" + series.author.discriminator
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
            "class": "series-update-time text-muted", "text": "Last updated " + format_str
        });
    } else {
        this.lastUpdated = null;
    }
}


function SeriesList(headerLetter, seriesList) {
    this.headerLetter = headerLetter;
    this.seriesList = seriesList;
    this.root = $("<div>", { "class": "series-list-container" });

    this.header = addSubelement(this.root, "h2", {
        "class": "series-list-header",
        "id": "index-" + headerLetter,
        "text": headerLetter
    });

    this.list = addSubelement(this.root, "ul", { "class": "series-list" });

    this.entries = seriesList.map(function (series) {
        return new SeriesEntry(series);
    });

    for (var entry of this.entries) {
        this.list.append(entry.root);
    }
}

function renderSeriesList() {
    fetch("/api/series").then(function (response) {
        return response.json();
    }).then(function (seriesData) {
        /* Sort by title */
        seriesData.sort((elemA, elemB) => {
            if (elemA.title < elemB.title) {
                return -1;
            } else if (elemA.title > elemB.title) {
                return 1;
            } else {
                return 0;
            }
        });

        /* Construct index based on first letter of titles */
        var index = {};
        for (let series of seriesData) {
            let firstLetter = series.title[0].toUpperCase();
            if (!index[firstLetter]) {
                index[firstLetter] = [];
            }

            index[firstLetter].push(series);
        }

        var indexElems = [];
        for (let letter of Object.keys(index)) {
            indexElems.push(new SeriesList(letter, index[letter]));
        }

        indexElems.sort((elemA, elemB) => {
            if (elemA.headerLetter < elemB.headerLetter) {
                return -1;
            } else if (elemA.headerLetter > elemB.headerLetter) {
                return 1;
            } else {
                return 0;
            }
        });

        var indexContainer = $("#index-container");
        for (let elem of indexElems) {
            indexContainer.append(elem.root);
        }
    });
}

$(function () {
    renderSeriesList();
});
