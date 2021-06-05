import $ from "jquery";
import { Author, MultiAuthorView } from "./Author";
import { Snippet, TrimmedSnippet, SnippetView } from "./Snippet";
import { addSubelement } from "../helper";

export interface BaseSeries {
    tag: string,
    title: string,
    authors: Author[],
    subscribers: Author[],
    updated?: number,
    url: string,
    warnings: string[],
    wordcount: number,
    can_edit: boolean
}

export interface Series extends BaseSeries {
    snippets: Snippet[]
}

export interface TrimmedSeries extends BaseSeries {
    snippets: TrimmedSnippet[]
}

class SnippetSequenceView {
    root: JQuery;
    snippets: SnippetView[];

    constructor(snippets: Snippet[]) {
        this.root = $("<div>", { "class": "series-snippets" });
        this.snippets = [];

        for (let snippet of snippets) {
            let view = new SnippetView(snippet);

            this.snippets.push(view);
            this.root.append(view.root);
            addSubelement(this.root, "hr", { "class": "snippet-separator" });
        }
    }
}

class SeriesHeader {
    root: JQuery;
    authorView: MultiAuthorView;

    constructor(series: Series) {
        this.root = $("<div>", { "class": "series-header" });

        addSubelement(this.root, "h1", {
            "class": "series-title",
            "text": series.title
        });

        this.authorView = new MultiAuthorView(series.authors);
        this.root.append(this.authorView.root);
    }
}

class SeriesView {
    series: Series;
    root: JQuery;
    seriesHeader: SeriesHeader;
    snippets: SnippetSequenceView;

    constructor(series: Series) {
        this.series = series;
        this.root = $("<div>", { "class": "series-container" });
        this.seriesHeader = new SeriesHeader(this.series);
        this.snippets = new SnippetSequenceView(this.series.snippets);

        this.root.append(this.seriesHeader.root, this.snippets.root);
    }
}

export default function renderSeries(series: Series) {
    var view = new SeriesView(series);
    $("#view-container").append(view.root);
}
