import type { components } from './schema'

type S = components['schemas']

/** Every generated schema, for enums and payloads without an alias below: Schemas['Region']. */
export type Schemas = S

export type User = S['UserOut']
export type Platform = S['PlatformOut']
export type Release = S['ReleaseOut']
export type ReleaseIn = S['ReleaseIn']
export type ReleasePatch = S['ReleasePatch']
export type Library = S['LibraryOut']
export type Member = S['MemberOut']
export type Item = S['ItemOut']
export type ItemIn = S['ItemIn']
export type ItemPatch = S['ItemPatch']
export type PublicItem = S['PublicItemOut']
export type GroupNode = S['GroupNodeOut']
export type Section = S['SectionOut']
export type Overview = S['OverviewOut']
export type OverviewIn = S['OverviewIn']
export type Location = S['LocationOut']
export type Person = S['PersonOut']
export type Loan = S['LoanOut']
export type CustomList = S['ListOut']
export type ListEntry = S['EntryOut']
export type Candidate = S['CandidateOut']
export type BarcodeLookup = S['BarcodeLookupOut']
export type Provider = S['ProviderOut']
export type Integration = S['IntegrationOut']
export type Fact = S['FactOut']
export type Work = S['WorkOut']
export type WorkPatch = S['WorkPatch']
export type Tracking = S['TrackingOut']
export type TrackingIn = S['TrackingIn']
export type TrackingPatch = S['TrackingPatch']
export type TakeOverIn = S['TakeOverIn']

/** Fields a library can be grouped and filtered by (backend: collection/selectors/grouping.py). */
export const GROUP_FIELDS = [
  'platform.name',
  'platform.manufacturer',
  'platform.year',
  'publisher.name',
  'game.kind',
  'game.franchises',
  'game.series',
  'game.genres',
  'game.developers',
  'game.modes',
  'game.perspectives',
  'game.languages',
  'game.letter',
  'release.year',
  'release.decade',
  'release.region',
  'release.age_rating',
  'release.players_offline',
  'release.players_online',
  'release.developers',
  'location.path',
  'location.name',
  'location.kind',
  'location.room',
  'location.shelf',
  'location.box',
  'owner.name',
  'loan.to',
  'loan.overdue',
  'copy.status',
  'copy.format',
  'copy.condition',
  'copy.completeness',
  'copy.progress',
  'copy.tags',
  'copy.added',
  'copy.acquired',
] as const
export type GroupField = (typeof GROUP_FIELDS)[number]

/** Groupings a public link may use (no people, places or prices). */
export const PUBLIC_GROUP_FIELDS: GroupField[] = [
  'platform.name',
  'platform.manufacturer',
  'platform.year',
  'publisher.name',
  'game.kind',
  'game.franchises',
  'game.series',
  'game.genres',
  'game.developers',
  'game.modes',
  'game.perspectives',
  'game.languages',
  'game.letter',
  'release.year',
  'release.decade',
  'release.region',
  'release.age_rating',
  'release.players_offline',
  'release.players_online',
  'release.developers',
  'copy.format',
  'copy.status',
  'copy.completeness',
]

/** Group key the backend uses for "no value". */
export const NONE_KEY = 'none'
