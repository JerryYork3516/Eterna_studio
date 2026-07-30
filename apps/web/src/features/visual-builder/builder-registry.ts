import { ABSTRACT_BUST_GENERATOR_VERSION } from "@eterna/shared-schema/abstract-bust-blueprint";
import {
  generateAbstractBust,
  type AbstractBustGenerator,
} from "./builders/abstract-particle-bust/index.ts";

export type VisualBuilderStatus = "available" | "unavailable";

export interface VisualBuilderDefinition {
  id: string;
  displayNameKey: string;
  appearanceType: string;
  generatorVersion: string;
  status: VisualBuilderStatus;
}

export const ABSTRACT_PARTICLE_BUST_BUILDER_ID = "abstract_particle_bust" as const;

const ABSTRACT_PARTICLE_BUST_BUILDER = Object.freeze({
  id: ABSTRACT_PARTICLE_BUST_BUILDER_ID,
  displayNameKey: "visualBuilder.builder.abstractParticleBust",
  appearanceType: "abstract_particle_bust",
  generatorVersion: ABSTRACT_BUST_GENERATOR_VERSION,
  status: "available",
} satisfies VisualBuilderDefinition);

export const VISUAL_BUILDER_DEFINITIONS: readonly VisualBuilderDefinition[] =
  Object.freeze([ABSTRACT_PARTICLE_BUST_BUILDER]);

const VISUAL_BUILDER_GENERATORS: Readonly<
  Record<typeof ABSTRACT_PARTICLE_BUST_BUILDER_ID, AbstractBustGenerator>
> = Object.freeze({
  [ABSTRACT_PARTICLE_BUST_BUILDER_ID]: generateAbstractBust,
});

export function getVisualBuilderDefinition(
  builderId: string
): VisualBuilderDefinition | null {
  return (
    VISUAL_BUILDER_DEFINITIONS.find(
      (definition) => definition.id === builderId
    ) ?? null
  );
}

export function requireVisualBuilderDefinition(
  builderId: string
): VisualBuilderDefinition {
  const definition = getVisualBuilderDefinition(builderId);
  if (!definition || definition.status !== "available") {
    throw new Error(`Unknown or unavailable visual builder: ${builderId}`);
  }
  return definition;
}

export function getVisualBuilderGenerator(
  builderId: string
): AbstractBustGenerator | null {
  return builderId === ABSTRACT_PARTICLE_BUST_BUILDER_ID
    ? VISUAL_BUILDER_GENERATORS[ABSTRACT_PARTICLE_BUST_BUILDER_ID]
    : null;
}

export function requireVisualBuilderGenerator(
  builderId: string
): AbstractBustGenerator {
  const generator = getVisualBuilderGenerator(builderId);
  if (!generator) {
    throw new Error(`Unknown visual builder generator: ${builderId}`);
  }
  return generator;
}
