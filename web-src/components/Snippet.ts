import $ from "jquery";
import * as markdown from 'simple-markdown';
import discordMarkdown from "discord-markdown";

import { addSubelement } from "../helper";

export interface TrimmedSnippet {
    author_id: number;
    message_id: number;
    channel_id: number;
}

export interface Snippet extends TrimmedSnippet {
    content: string;
    attachment_urls: string[];
}

function checkImage(url: string): { isImage: boolean, isSpoiler: boolean } {
    var parsed = new URL(url);
    var ret = { isImage: false, isSpoiler: false };

    var dotIdx = parsed.pathname.lastIndexOf(".");
    if (dotIdx >= 0) {
        let extension = parsed.pathname.substring(dotIdx + 1).toLowerCase();
        if (extension === "jpg" || extension === "jpeg" || extension === "png" || extension === "gif" || extension === "webp") {
            let slashIdx = parsed.pathname.lastIndexOf("/");
            let filename = parsed.pathname.substring(slashIdx + 1);

            ret.isImage = true;
            if (filename.startsWith("SPOILER_")) {
                ret.isSpoiler = true;
            }
        }
    }

    return ret;
}

discordMarkdown.rules.url.html = function (node: unknown, output: (content: string, state?: markdown.State) => string, state?: markdown.State): string {
    // @ts-ignore
    var sanitizedURL = discordMarkdown.markdownEngine.sanitizeUrl(node.target) || "";
    var imageStatus = checkImage(sanitizedURL);
    var content = null;

    if (imageStatus.isImage) {
        let imgTag = discordMarkdown.htmlTag(
            'img', "", {
            src: sanitizedURL,
            class: "d-img" + (imageStatus.isSpoiler ? " d-img-spoiler" : "")
        }, false);

        let wrapperContent = discordMarkdown.htmlTag('a', imgTag, {
            href: sanitizedURL,
            class: "d-link",
            target: "_blank",
        }, true, state);

        if (imageStatus.isSpoiler) {
            let label = discordMarkdown.htmlTag('span', "Spoiler", {
                class: "d-spoiler-img-label"
            }, true, state);

            wrapperContent += discordMarkdown.htmlTag('div', label, {
                class: "d-spoiler-cover"
            }, true, state);
        }

        return discordMarkdown.htmlTag('div', wrapperContent, {
            class: "d-img-wrapper"
        }, true, state);
    } else {
        // @ts-ignore
        return discordMarkdown.htmlTag('a', output(node.content, state), {
            href: sanitizedURL,
            class: "d-link",
            target: "_blank",
        }, true, state);
    }
}

class AttachmentImage {
    attachment_url: string;
    root: JQuery;

    constructor(attachment_url: string) {
        this.attachment_url = attachment_url;
        this.root = $("<div>", { "class": "d-attachment-wrapper d-img-wrapper" });

        var imgStatus = checkImage(attachment_url);

        var linkElem = addSubelement(this.root, "a", {
            "href": attachment_url,
            "class": "d-link",
            "target": "_blank"
        });

        var imgElem = addSubelement(linkElem, "img", {
            "src": attachment_url,
            "class": "d-img" + (imgStatus.isSpoiler ? " d-img-spoiler" : "")
        });

        if (imgStatus.isSpoiler) {
            let coverElem = addSubelement(this.root, "div", {
                class: "d-spoiler-cover"
            });

            addSubelement(coverElem, "span", {
                text: "Spoiler",
                class: "d-spoiler-img-label"
            });
        }
    }
}

export class SnippetView {
    snippet: Snippet;
    root: JQuery;
    attachment_views: AttachmentImage[];

    constructor(snippet: Snippet) {
        this.snippet = snippet;
        this.root = $("<div>", {
            "id": "snippet-" + snippet.message_id,
            "class": "snippet-container"
        });
        this.attachment_views = [];

        var snippetElem = addSubelement(this.root, "div", { "class": "snippet" });
        snippetElem[0].innerHTML = discordMarkdown.toHTML(snippet.content);

        snippetElem.find(".d-spoiler").on("click", (ev) => {
            $(ev.target).toggleClass("d-spoiler-show");
        });

        for (let attachment_url of snippet.attachment_urls) {
            let view = new AttachmentImage(attachment_url);

            this.attachment_views.push(view);
            snippetElem.append(view.root);
        }

        $(snippetElem).find(".d-img-wrapper").each((idx, elem) => {
            $(elem).find(".d-spoiler-cover").on("click", (ev) => {
                $(elem).find(".d-img-spoiler").removeClass("d-img-spoiler");
                $(ev.target).hide();
            });
        })
    }
}
