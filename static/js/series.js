function checkImage(url) {
    url = new URL(url);
    var ret = { isImage: false, isSpoiler: false };

    var dotIdx = url.pathname.lastIndexOf(".");
    if (dotIdx >= 0) {
        let extension = url.pathname.substring(dotIdx + 1).toLowerCase();
        if (extension === "jpg" || extension === "jpeg" || extension === "png" || extension === "gif" || extension === "webp") {
            let slashIdx = url.pathname.lastIndexOf("/");
            let filename = url.pathname.substring(slashIdx + 1);

            ret.isImage = true;
            if (filename.startsWith("SPOILER_")) {
                ret.isSpoiler = true;
            }
        }
    }

    return ret;
}

discordMarkdown.rules.url.html = (node, output, state) => {
    var sanitizedURL = discordMarkdown.markdownEngine.sanitizeUrl(node.target);
    var imageStatus = checkImage(sanitizedURL);
    var content = null;

    if (imageStatus.isImage) {
        let imgTag = discordMarkdown.htmlTag(
            'img', null, {
            src: sanitizedURL,
            class: "d-img" + (imageStatus.isSpoiler ? " d-img-spoiler" : "")
        }, false);

        let wrapperContent = discordMarkdown.htmlTag('a', imgTag, {
            href: sanitizedURL,
            class: "d-link",
            target: "_blank",
        }, state);

        if (imageStatus.isSpoiler) {
            let label = discordMarkdown.htmlTag('span', "Spoiler", {
                class: "d-spoiler-img-label"
            }, state);

            wrapperContent += discordMarkdown.htmlTag('div', label, {
                class: "d-spoiler-cover"
            }, state);
        }

        return discordMarkdown.htmlTag('div', wrapperContent, {
            class: "d-img-wrapper"
        }, state);
    } else {
        return discordMarkdown.htmlTag('a', output(node.content, state), {
            href: sanitizedURL,
            class: "d-link",
            target: "_blank",
        }, state);
    }
}

function renderSnippet(message_id, escaped_content, attachment_urls) {
    var container = document.getElementById("snippet-" + message_id);
    container.innerHTML = discordMarkdown.toHTML(escaped_content);

    $(".d-spoiler", container).click((ev) => {
        $(ev.target).toggleClass("d-spoiler-show");
    });

    for (let attachment_url of attachment_urls) {
        var imgStatus = checkImage(attachment_url);
        var linkElem = $("<a>", {
            "href": attachment_url,
            "class": "d-link",
            "target": "_blank"
        });
        var wrapper = $("<div>", {
            "class": "d-attachment-wrapper" + (imgStatus.isImage ? " d-img-wrapper" : "")
        });

        $(wrapper).append(linkElem);

        if (imgStatus.isImage) {
            let imgElem = $("<img>", {
                "src": attachment_url,
                "class": "d-img" + (imgStatus.isSpoiler ? " d-img-spoiler" : "")
            });

            $(linkElem).append(imgElem);

            if (imgStatus.isSpoiler) {
                let coverElem = $("<div>", {
                    class: "d-spoiler-cover"
                });

                let labelElem = $("<span>", {
                    text: "Spoiler",
                    class: "d-spoiler-img-label"
                });

                $(coverElem).append(labelElem);
                $(wrapper).append(coverElem);
            }
        }

        $(container).append(wrapper);
    }

    $(".d-img-wrapper", container).each((idx, wrapperElem) => {
        $(".d-spoiler-cover", wrapperElem).on("click", (ev) => {
            $(".d-img-spoiler", wrapperElem).removeClass("d-img-spoiler");
            $(ev.target).hide();
        });
    })
}
