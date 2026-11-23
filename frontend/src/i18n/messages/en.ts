import { collectMessages, type Messages } from '../collect'

/** All English messages in one chunk, loaded only when English is the language. */
export default collectMessages(
  import.meta.glob<Messages>(
    ['../locales/en.json', '../../features/*/locales/en.json', '../../addons/*/locales/en.json'],
    {
      eager: true,
      import: 'default',
    },
  ),
).en
