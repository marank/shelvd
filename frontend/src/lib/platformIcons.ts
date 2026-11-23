import {
  Disc3,
  Film,
  Gamepad,
  Gamepad2,
  GamepadDirectional,
  Glasses,
  Joystick,
  Laptop,
  MemoryStick,
  Monitor,
  Smartphone,
  Tablet,
  ToyBrick,
  Tv,
  type LucideIcon,
} from '@lucide/vue'

/** The platform symbols to choose from (keys = backend PlatformIcon). Neutral shapes, no
 * logos: those are the manufacturers' trademarks; people can upload their own icon. */
export const PLATFORM_ICONS: Record<string, LucideIcon> = {
  console: Gamepad2,
  controller: Gamepad,
  joystick: Joystick,
  handheld: GamepadDirectional,
  tablet: Tablet,
  phone: Smartphone,
  pc: Monitor,
  laptop: Laptop,
  tv: Tv,
  disc: Disc3,
  cartridge: MemoryStick,
  vr: Glasses,
  figure: ToyBrick,
  film: Film,
}
