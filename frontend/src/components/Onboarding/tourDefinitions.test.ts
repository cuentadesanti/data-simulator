/**
 * @vitest-environment jsdom
 */
import { describe, it, expect } from 'vitest';
import { tourDefinitions, inspectorHintStep } from './tourDefinitions';
import type { TourId } from './types';

describe('tourDefinitions', () => {
  const allTourIds: TourId[] = ['main', 'source', 'transform', 'model', 'publish'];

  it('has definitions for all tour IDs', () => {
    allTourIds.forEach((id) => {
      expect(tourDefinitions[id]).toBeDefined();
      expect(tourDefinitions[id].id).toBe(id);
    });
  });

  it('all tours have valid step ids in "tourId.stepName" format', () => {
    allTourIds.forEach((tourId) => {
      const tour = tourDefinitions[tourId];
      tour.steps.forEach((step) => {
        expect(step.id).toMatch(new RegExp(`^${tourId}\\.`));
      });
    });
  });

  it('all steps have non-empty title and content', () => {
    allTourIds.forEach((tourId) => {
      const tour = tourDefinitions[tourId];
      tour.steps.forEach((step) => {
        expect(step.title.length).toBeGreaterThan(0);
        expect(step.content.length).toBeGreaterThan(0);
      });
    });
  });

  it('all tours have at least one step', () => {
    allTourIds.forEach((tourId) => {
      expect(tourDefinitions[tourId].steps.length).toBeGreaterThan(0);
    });
  });

  it('all tours have version >= 1', () => {
    allTourIds.forEach((tourId) => {
      expect(tourDefinitions[tourId].version).toBeGreaterThanOrEqual(1);
    });
  });

  it('floating steps have null target', () => {
    allTourIds.forEach((tourId) => {
      const tour = tourDefinitions[tourId];
      tour.steps.forEach((step) => {
        if (step.floating) {
          expect(step.target).toBeNull();
        }
      });
    });
  });

  it('non-floating steps have a data-tour selector target', () => {
    allTourIds.forEach((tourId) => {
      const tour = tourDefinitions[tourId];
      tour.steps.forEach((step) => {
        if (!step.floating && step.target) {
          expect(step.target).toMatch(/^\[data-tour="[a-z-]+"]/);
        }
      });
    });
  });

  it('inspectorHintStep is properly defined', () => {
    expect(inspectorHintStep.id).toBe('inspector.hint');
    expect(inspectorHintStep.target).toMatch(/data-tour/);
    expect(inspectorHintStep.title.length).toBeGreaterThan(0);
  });

  it('stage tours have completionAction defined', () => {
    const stageTours: TourId[] = ['source', 'transform', 'model', 'publish'];
    stageTours.forEach((tourId) => {
      expect(tourDefinitions[tourId].completionAction).toBeDefined();
      expect(typeof tourDefinitions[tourId].completionAction).toBe('string');
    });
  });
});
