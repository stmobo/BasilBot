import $ from "jquery";
import { MultiAuthorView } from "./Author";
import { BaseSeries, TrimmedSeries } from "./Series";
import { addSubelement, formatTimeSinceEvent } from "../helper";
import { LoginData, getLoginInfo } from "../User";


function compareArrays<T>(a: T[], b: T[], compareFunc: (a: T, b: T) => number): number {
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

function compareByTitle(elemA: BaseSeries, elemB: BaseSeries) {
    if (elemA.title < elemB.title) {
        return -1;
    } else if (elemA.title > elemB.title) {
        return 1;
    } else {
        return 0;
    }
}

function compareByAuthors(elemA: BaseSeries, elemB: BaseSeries) {
    return compareArrays(elemA.authors, elemB.authors, (authorA, authorB) => compareArrays(
        [authorA.display_names.join(""), authorA.username, authorA.discriminator],
        [authorB.display_names.join(""), authorB.username, authorB.discriminator],
        (a, b) => (a > b ? 1 : (a < b ? -1 : 0))
    ));
}

class SeriesTitlebar {
    root: JQuery;
    titleInput: JQuery<HTMLInputElement>;
    link: JQuery<HTMLAnchorElement>;
    authorView: MultiAuthorView;
    defaultTitle: string;

    constructor(series: TrimmedSeries) {
        this.defaultTitle = series.title;
        this.root = $("<div>", { "class": "series-titlebar" });

        this.titleInput = $(document.createElement("input")).attr({
            "type": "text",
            "class": "series-title-input form-control",
            "placeholder": "Series Title"
        }).appendTo(this.root).hide();

        this.link = $(document.createElement("a")).attr({
            "class": "series-link",
            "href": series.url,
        }).text(series.title).appendTo(this.root);

        this.authorView = new MultiAuthorView(series.authors);
        this.root.append("by");
        this.root.append(this.authorView.root);

        this.inputValue = this.defaultTitle;
    }

    get inputValue(): string {
        return this.titleInput[0].value;
    }

    set inputValue(value: string) {
        this.titleInput[0].value = value;
    }

    get valueChanged(): boolean {
        return this.inputValue !== this.defaultTitle;
    }

    toggleInput(visible: boolean) {
        if (visible) {
            this.inputValue = this.defaultTitle;
            this.link.hide();
            this.titleInput.show();
        } else {
            this.titleInput.hide();
            this.link.show();
        }
    }
}

class TagInputBar {
    root: JQuery;
    tagInput: JQuery<HTMLInputElement>;
    defaultTag: string;

    constructor(series: TrimmedSeries) {
        this.defaultTag = series.tag;
        this.root = $("<div>", { "class": "series-tag-edit-bar" });

        addSubelement(this.root, "label", {
            "class": "series-tag-input-label",
            "text": "Change Series Tag: ",
            "for": "tag-edit-" + series.tag,
        });

        this.tagInput = $(document.createElement("input")).attr({
            "type": "text",
            "class": "series-tag-input form-control",
            "placeholder": "Series Tag",
            "id": "tag-edit-" + series.tag
        }).appendTo(this.root);

        this.inputValue = this.defaultTag;
    }

    get inputValue(): string {
        return this.tagInput[0].value;
    }

    set inputValue(value: string) {
        this.tagInput[0].value = value;
    }

    get valueChanged(): boolean {
        return this.inputValue !== this.defaultTag;
    }

    toggleInput(visible: boolean) {
        if (visible) {
            this.inputValue = this.defaultTag;
            this.root.show();
        } else {
            this.root.hide();
        }
    }
}

class ContentWarningBar {
    root: JQuery;

    constructor(series: TrimmedSeries) {
        this.root = $("<div>", {
            "class": "series-content-warnings",
            "text": "CW" + (series.warnings.length > 1 ? "s" : "") + ": " + series.warnings.join(", ")
        });
    }
}

class SeriesInfoView {
    root: JQuery;
    editErrorText: JQuery;

    constructor(series: TrimmedSeries) {
        this.root = $("<div>", { "class": "series-info-container" });

        addSubelement(this.root, "span", {
            "class": "series-part-count",
            "text": series.snippets.length.toString() + " part" + (series.snippets.length != 1 ? "s" : "")
        });

        addSubelement(this.root, "span", {
            "class": "series-word-count",
            "text": series.wordcount.toString() + " word" + (series.wordcount != 1 ? "s" : "")
        });

        if (series.updated) {
            addSubelement(this.root, "span", {
                "class": "series-update-time",
                "text": "Last updated " + formatTimeSinceEvent(series.updated)
            });
        }

        this.editErrorText = addSubelement(this.root, "span", {
            "class": "series-edit-error",
            "text": ""
        }).hide();
    }

    setErrorText(text?: string) {
        if (text) {
            this.editErrorText.text(text).show();
        } else {
            this.editErrorText.text("").hide();
        }
    }
}

class ConfirmButtons {
    root: JQuery;
    confirmBtn: JQuery;
    cancelBtn: JQuery;

    onConfirm: (ev: JQuery.Event) => void;
    onCancel: (ev: JQuery.Event) => void;

    constructor(confirmText: string, confirmClasses: string, cancelClasses: string, onConfirm: (ev: JQuery.Event) => void, onCancel: (ev: JQuery.Event) => void, label?: string) {
        this.root = $("<div>", { "class": "series-btn-container" });
        this.onConfirm = onConfirm;
        this.onCancel = onCancel;

        if (label) {
            addSubelement(this.root, "span", {
                "class": "series-confirm-label me-3",
                "text": label
            });
        }

        this.confirmBtn = addSubelement(this.root, "button", {
            "class": "btn btn-sm me-3 " + confirmClasses,
            "text": confirmText
        });

        this.cancelBtn = addSubelement(this.root, "button", {
            "class": "btn btn-sm " + cancelClasses,
            "text": "Cancel"
        });
    }

    toggleVisible(show: boolean) {
        if (show) {
            this.root.show();
            this.confirmBtn.on("click", this.doSave.bind(this));
            this.cancelBtn.on("click", this.doCancel.bind(this));
        } else {
            this.root.hide();
            this.confirmBtn.off("click");
            this.cancelBtn.off("click");
        }
    }

    doSave(ev: JQuery.Event) {
        this.toggleVisible(false);
        this.onConfirm(ev);
    }

    doCancel(ev: JQuery.Event) {
        this.toggleVisible(false);
        this.onCancel(ev);
    }
}

class SeriesEditControls {
    series: TrimmedSeries;

    infoView: SeriesInfoView;
    titlebar: SeriesTitlebar;
    tagInputBar: TagInputBar;

    mainButtonRow: JQuery;
    editTitleBtn: JQuery;
    editTagBtn: JQuery;
    deleteBtn: JQuery;

    confirmEditButtons: ConfirmButtons;
    confirmDeleteButtons: ConfirmButtons;

    constructor(series: TrimmedSeries, infoView: SeriesInfoView, titlebar: SeriesTitlebar, tagInputBar: TagInputBar) {
        this.series = series;
        this.infoView = infoView;
        this.titlebar = titlebar;
        this.tagInputBar = tagInputBar;

        this.mainButtonRow = $("<div>", { "class": "series-btn-container" });

        this.editTagBtn = addSubelement(this.mainButtonRow, "button", {
            "class": "btn btn-success btn-sm me-3",
            "text": "Change Tag",
        }).on("click", this.startEditTag.bind(this));

        this.editTitleBtn = addSubelement(this.mainButtonRow, "button", {
            "class": "btn btn-success btn-sm me-3",
            "text": "Edit Title",
        }).on("click", this.startEditTitle.bind(this));

        this.deleteBtn = addSubelement(this.mainButtonRow, "button", {
            "class": "btn btn-danger btn-sm",
            "text": "Delete",
        }).on("click", this.startDelete.bind(this));

        this.confirmEditButtons = new ConfirmButtons(
            "Save", "btn-success", "btn-primary",
            this.saveChanges.bind(this), this.cancel.bind(this)
        );

        this.confirmDeleteButtons = new ConfirmButtons(
            "Delete", "btn-danger", "btn-primary",
            this.deleteSeries.bind(this), this.cancel.bind(this),
            "Are you sure?"
        );

        this.tagInputBar.toggleInput(false);
        this.titlebar.toggleInput(false);
        this.confirmEditButtons.toggleVisible(false);
        this.confirmDeleteButtons.toggleVisible(false);
    }

    startEditTag() {
        this.infoView.setErrorText();
        this.tagInputBar.toggleInput(true);
        this.mainButtonRow.hide();
        this.confirmEditButtons.toggleVisible(true);
    }

    startEditTitle() {
        this.infoView.setErrorText();
        this.titlebar.toggleInput(true);
        this.mainButtonRow.hide();
        this.confirmEditButtons.toggleVisible(true);
    }

    startDelete() {
        this.infoView.setErrorText();
        this.mainButtonRow.hide();
        this.confirmDeleteButtons.toggleVisible(true);
    }

    cancel(ev: JQuery.Event) {
        this.infoView.setErrorText();
        this.titlebar.toggleInput(false);
        this.tagInputBar.toggleInput(false);
        this.confirmEditButtons.toggleVisible(false);
        this.confirmDeleteButtons.toggleVisible(false);
        this.mainButtonRow.show();
    }

    saveChanges(ev: JQuery.Event) {
        if (this.tagInputBar.valueChanged || this.titlebar.valueChanged) {
            let body: { tag?: string, title?: string } = {};

            if (this.tagInputBar.valueChanged) {
                body.tag = this.tagInputBar.inputValue;
            }

            if (this.titlebar.valueChanged) {
                body.title = this.titlebar.inputValue;
            }

            fetch("/api/series/" + encodeURIComponent(this.series.tag), {
                "method": "PATCH",
                "headers": {
                    "Content-Type": "application/json",
                },
                "body": JSON.stringify(body)
            }).then((resp) => {
                if (resp.ok) {
                    window.location.reload();
                    return "";
                } else {
                    return resp.text();
                }
            }).then((text) => {
                this.infoView.setErrorText(text);
            });
        } else {
            this.cancel(ev);
        }
    }

    deleteSeries(ev: JQuery.Event) {
        fetch("/api/series/" + encodeURIComponent(this.series.tag), {
            "method": "DELETE"
        }).then((resp) => {
            if (resp.ok) {
                window.location.reload();
                return "";
            } else {
                return resp.text();
            }
        }).then((text) => {
            this.infoView.setErrorText(text);
        });
    }
}

class SeriesIndexEntry {
    root: JQuery;
    series: TrimmedSeries;

    titleBar: SeriesTitlebar;
    infoView: SeriesInfoView;

    contentWarningBar?: ContentWarningBar;
    tagInputBar?: TagInputBar;
    editControls?: SeriesEditControls;

    constructor(series: TrimmedSeries) {
        this.series = series;
        this.root = $("<li>", { "class": "series-entry" });
        this.titleBar = new SeriesTitlebar(series);
        this.infoView = new SeriesInfoView(series);

        var infoBar = $("<div>", { "class": "series-infobar" }).append(this.infoView.root);
        this.root.append(this.titleBar.root);

        if (series.can_edit) {
            this.tagInputBar = new TagInputBar(series);
            this.editControls = new SeriesEditControls(series, this.infoView, this.titleBar, this.tagInputBar);

            this.root.append(this.tagInputBar.root);
            infoBar.append(
                this.editControls.mainButtonRow,
                this.editControls.confirmEditButtons.root,
                this.editControls.confirmDeleteButtons.root
            );
        }

        if (series.warnings.length > 0) {
            this.contentWarningBar = new ContentWarningBar(series);
            this.root.append(this.contentWarningBar.root);
        }

        this.root.append(infoBar);
    }
}

class SeriesList {
    root: JQuery;
    navItem: JQuery;

    key: string;
    sortKey: string;
    id: string;
    entries: SeriesIndexEntry[];

    constructor(key: string, keyType: string, seriesList: TrimmedSeries[]) {
        this.key = key;
        this.sortKey = key.toLowerCase();
        this.id = keyType + "-index-" + key;
        this.root = $("<div>", { "class": "series-list-container" });

        addSubelement(this.root, "h2", {
            "class": "series-list-header",
            "id": this.id,
            "text": this.key
        });

        var listElem = addSubelement(this.root, "ul", { "class": "series-list" });
        this.entries = seriesList.map((s) => new SeriesIndexEntry(s));
        listElem.append(this.entries.map((elem) => elem.root));

        this.navItem = $("<li>", { "class": "nav-item index-nav-item" });
        addSubelement(this.navItem, "a", { "class": "nav-link", "href": "#" + this.id, "text": this.key });
    }
}

class SeriesIndex {
    root: JQuery;
    tab: JQuery;
    seriesData: TrimmedSeries[];
    seriesLists: SeriesList[];

    constructor(seriesData: TrimmedSeries[], byAuthor: boolean) {
        this.root = $("<div>", { "class": "series-index-wrapper" });

        this.tab = $("<li>", { "class": "nav-item" });
        addSubelement(this.tab, "button", {
            "class": "nav-link",
            "text": "By " + (byAuthor ? "Author" : "Title")
        });

        var indexNav = addSubelement(this.root, "ul", { "class": "nav" });
        var indexContainer = addSubelement(this.root, "div", { "class": "series-index" });

        /* Sort by specified key */
        this.seriesData = seriesData.slice();
        this.seriesData.sort(byAuthor ? compareByAuthors : compareByTitle);

        /* Construct index */
        var index: { [key: string]: TrimmedSeries[] } = {};

        for (let series of this.seriesData) {
            let keys = [];
            if (byAuthor) {
                for (let author of series.authors) {
                    let disp_names = author.display_names.join(" / ");
                    keys.push(disp_names + " (" + author.username + "#" + author.discriminator + ")");
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

        this.seriesLists = Object.keys(index).map((key) => new SeriesList(
            key, byAuthor ? "author" : "title", index[key]
        ));

        this.seriesLists.sort((elemA, elemB) => {
            if (elemA.sortKey < elemB.sortKey) {
                return -1;
            } else if (elemA.sortKey > elemB.sortKey) {
                return 1;
            } else {
                return 0;
            }
        });

        indexContainer.append(this.seriesLists.map((elem) => elem.root));
        indexNav.append(this.seriesLists.map((elem) => elem.navItem));

        this.tab.on("click", (ev) => this.toggleVisible(true));
    }

    toggleVisible(visible: boolean) {
        if (visible) {
            this.tab.addClass("active");
            this.root.show();
        } else {
            this.tab.removeClass("active");
            this.root.hide();
        }
    }
}

export default function renderIndices(): Promise<void> {
    return fetch("/api/series").then((resp) => resp.json()).then((seriesData: TrimmedSeries[]) => {
        var titleIndex = new SeriesIndex(seriesData, false);
        var authorIndex = new SeriesIndex(seriesData, true);

        titleIndex.tab.on("click", (ev) => authorIndex.toggleVisible(false));
        authorIndex.tab.on("click", (ev) => titleIndex.toggleVisible(false));

        var tabContainer = $("#index-tab");
        var tabContent = $("#index-tab-content");

        tabContainer.append(titleIndex.tab, authorIndex.tab);
        tabContent.append(titleIndex.root, authorIndex.root);

        titleIndex.toggleVisible(true);
        authorIndex.toggleVisible(false);
    });
}
