import $ from 'jquery';
import { addSubelement } from "../helper";

export interface Author {
    id: number;
    display_names: string[];
    username: string;
    discriminator: string;
}

class AuthorView {
    author: Author;
    root: JQuery;

    constructor(author: Author) {
        this.author = author;
        this.root = $("<span>", { "class": "author-container" });

        addSubelement(this.root, "span", {
            "class": "author-display-name",
            "text": author.display_names.join(" / ")
        });

        var usernameContainer = addSubelement(this.root, "span", {
            "class": "author-username-container"
        });

        addSubelement(usernameContainer, "span", {
            "class": "author-username",
            "text": author.username
        });

        addSubelement(usernameContainer, "span", {
            "class": "author-discriminator",
            "text": author.discriminator
        });
    }
}

export class MultiAuthorView {
    root: JQuery;
    subviews: AuthorView[];

    constructor(authors: Author[]) {
        this.root = $("<div>", { "class": "series-authors" });
        this.subviews = authors.map((author) => new AuthorView(author));

        this.subviews.forEach((view, idx, arr) => {
            if (arr.length > 1 && idx > 0) {
                this.root.append(
                    (arr.length > 2 ? ", " : " ") +
                    (idx === arr.length - 1 ? "and " : "")
                );
            }

            this.root.append(view.root);
        });
    }
}
