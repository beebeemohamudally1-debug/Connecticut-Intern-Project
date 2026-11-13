
document.addEventListener('DOMContentLoaded', function () {
    const dropdown = document.querySelector('[data-notification-dropdown]');
    if (!dropdown) return;

    const toggle = dropdown.querySelector('[data-notification-toggle]');
    const popup = dropdown.querySelector('[data-notification-popup]');
    const list = dropdown.querySelector('[data-notification-list]');
    const badge = dropdown.querySelector('[data-notification-count]');
    const readAllButton = dropdown.querySelector('[data-notification-read-all]');

    const listUrl = dropdown.dataset.listUrl;
    const countUrl = dropdown.dataset.countUrl;
    const readAllUrl = dropdown.dataset.readAllUrl;
    const readUrlTemplate = dropdown.dataset.readUrlTemplate;

    function getCSRFToken() {
        const cookie = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));

        return cookie
            ? decodeURIComponent(cookie.split('=').slice(1).join('='))
            : '';
    }

    async function getJSON(url, options = {}) {
        const response = await fetch(url, {
            credentials: 'same-origin',
            ...options
        });

        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }

        return response.json();
    }

    async function updateCount() {
        const data = await getJSON(countUrl);
        const count = data.unread_count;

        badge.textContent = count;
        badge.hidden = count === 0;

        toggle.setAttribute(
            'aria-label',
            `Notifications, ${count} unread`
        );
    }

    function createNotificationItem(notification) {
        const button = document.createElement('button');

        button.type = 'button';
        button.className = 'notification-popup-item';

        if (!notification.is_read) {
            button.classList.add('unread');
        }

        const title = document.createElement('strong');
        title.textContent = notification.title;

        const message = document.createElement('span');
        message.textContent = notification.message;

        const date = document.createElement('span');

        date.textContent = new Date(
            notification.created_at
        ).toLocaleString('en-MU', {
            dateStyle: 'medium',
            timeStyle: 'short'
        });

        button.append(title, message, date);

        
button.addEventListener('click', async function () {
    button.disabled = true;

    try {
        if (!notification.is_read) {
            const url = readUrlTemplate.replace(
                /\/0\/read\/$/,
                `/${notification.id}/read/`
            );

            await getJSON(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                }
            });

            notification.is_read = true;
            button.classList.remove('unread');

            await updateCount();
        }

        // Open the relevant page, even if already read.
        if (notification.url) {
            const destination = new URL(
                notification.url,
                window.location.origin
            );

            if (destination.origin === window.location.origin) {
                window.location.assign(destination.href);
            }
        }

    } catch (error) {
        console.error(error);
        alert('Could not open this notification.');
    } finally {
        button.disabled = false;
    }
});

           

           
return button;
    
}
    async function loadNotifications() {
        list.replaceChildren();

        const loading = document.createElement('p');
        loading.textContent = 'Loading notifications...';
        list.appendChild(loading);

        try {
            const data = await getJSON(listUrl);

            const notifications = data.notifications
                .slice()
                .sort((a, b) =>
                    new Date(b.created_at) - new Date(a.created_at)
                )
                .slice(0, 5);

            list.replaceChildren();

            if (notifications.length === 0) {
                const empty = document.createElement('p');
                empty.textContent = 'No notifications yet.';
                list.appendChild(empty);
                return;
            }

            notifications.forEach(notification => {
                list.appendChild(
                    createNotificationItem(notification)
                );
            });

        } catch (error) {
            console.error(error);
            list.replaceChildren();

            const message = document.createElement('p');
            message.textContent = 'Unable to load notifications.';
            list.appendChild(message);
        }
    }

    toggle.addEventListener('click', async function () {
        const opening = popup.hidden;

        popup.hidden = !opening;
        toggle.setAttribute('aria-expanded', String(opening));

        if (opening) {
            await Promise.allSettled([
                loadNotifications(),
                updateCount()
            ]);
        }
    });

    readAllButton.addEventListener('click', async function () {
        readAllButton.disabled = true;

        try {
            await getJSON(readAllUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                }
            });

            await Promise.all([
                loadNotifications(),
                updateCount()
            ]);

        } catch (error) {
            console.error(error);
            alert('Could not mark all notifications as read.');
        } finally {
            readAllButton.disabled = false;
        }
    });

    document.addEventListener('click', function (event) {
        if (!dropdown.contains(event.target)) {
            popup.hidden = true;
            toggle.setAttribute('aria-expanded', 'false');
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && !popup.hidden) {
            popup.hidden = true;
            toggle.setAttribute('aria-expanded', 'false');
            toggle.focus();
        }
    });

    updateCount().catch(console.error);
});
