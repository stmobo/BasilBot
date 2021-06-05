import $ from "jquery";
import { Author } from "./components/Author";

export interface LoginData {
    session_id: string;
    dev_mode: boolean;
    user_data?: Author;
}

// @ts-ignore
var CURRENT_USER: LoginData = undefined;

export function getLoginInfo(): Promise<LoginData> {
    if (CURRENT_USER) {
        return Promise.resolve(CURRENT_USER);
    } else {
        return fetch("/api/auth/me").then((resp) => resp.json()).then((data) => {
            CURRENT_USER = data;
            if (CURRENT_USER.user_data) {
                $("#login-btn").hide();
                $("#cur-user-name").text(CURRENT_USER.user_data.username + "#" + CURRENT_USER.user_data.discriminator);
                $("#cur-user-label").show();
                $("#logout-btn").show();
            } else {
                $("#cur-user-label").hide();
                $("#logout-btn").hide();
                $("#login-btn").show();
            }

            return CURRENT_USER;
        });
    }
}

