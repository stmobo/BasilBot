import $ from 'jquery';

export function addSubelement(elem: JQuery | HTMLElement, elemType: string, opts: Object): JQuery<HTMLElement> {
    var new_elem = $("<" + elemType + ">", opts);
    $(elem).append(new_elem);

    return new_elem;
}

export function formatTimeSinceEvent(timestamp: number): string {
    var now = new Date();

    var elapsed_time = now.getTime() - Math.round(timestamp * 1000);

    if (elapsed_time < 5 * 60 * 1000) {
        // <5 minutes ago - display 'just now'
        return 'just now';
    } else if (elapsed_time < 60 * 60 * 1000) {
        // < 1 hour ago - display minutes since event
        return Math.floor(elapsed_time / (60 * 1000)) + ' minutes ago';
    } else if (elapsed_time < 24 * 60 * 60 * 1000) {
        // < 1 day ago - display hours since event
        let n_hours = Math.floor(elapsed_time / (60 * 60 * 1000));
        return n_hours + (n_hours === 1 ? ' hour ago' : ' hours ago');
    } else {
        // otherwise just display days since event
        let n_days = Math.floor(elapsed_time / (24 * 60 * 60 * 1000));
        return n_days + (n_days === 1 ? ' day ago' : ' days ago');
    }
}
