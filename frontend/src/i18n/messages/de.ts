import { collectMessages, type Messages } from '../collect'

/** All German messages in one chunk, loaded only when German is the language. */
export default collectMessages(
  import.meta.glob<Messages>(
    ['../locales/de.json', '../../features/*/locales/de.json', '../../addons/*/locales/de.json'],
    {
      eager: true,
      import: 'default',
    },
  ),
).de
