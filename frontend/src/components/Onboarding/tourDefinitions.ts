/**
 * Tour target convention:
 * - All targets use [data-tour="name"] attribute selectors
 * - Names are kebab-case, scoped: "component-element" (e.g. "stage-action-bar")
 * - Add new targets to this registry when extending tours
 * - Never remove a target without checking tourDefinitions for references
 */

import type { TourDefinition, TourId } from './types';

export const tourDefinitions: Record<TourId, TourDefinition> = {
  main: {
    id: 'main',
    version: 1,
    steps: [
      {
        id: 'main.welcome',
        target: null,
        title: 'Welcome to Data Simulator',
        content: 'Build synthetic datasets in four steps: Source, Transform, Model, and Publish.',
        position: 'bottom',
        floating: true,
      },
      {
        id: 'main.header',
        target: '[data-tour="global-header"]',
        title: 'Project Header',
        content: 'Save your work and share versions with your team from here.',
        position: 'bottom',
      },
      {
        id: 'main.left_rail',
        target: '[data-tour="left-rail"]',
        title: 'Workspace Navigator',
        content: 'Navigate between the four stages of your workflow using this sidebar.',
        position: 'right',
      },
      {
        id: 'main.stage_nav',
        target: '[data-tour="stage-nav"]',
        title: 'Stage Navigation',
        content: 'Source, Transform, Model, Publish — each stage builds on the previous one.',
        position: 'right',
      },
      {
        id: 'main.action_bar',
        target: '[data-tour="stage-action-bar"]',
        title: 'Stage Actions',
        content: 'Actions change based on the current stage. This bar shows what you can do right now.',
        position: 'bottom',
      },
      {
        id: 'main.canvas',
        target: '[data-tour="main-content"]',
        title: 'Your Canvas',
        content: 'This is where the magic happens. Each stage has its own workspace area.',
        position: 'top',
      },
      {
        id: 'main.ready',
        target: null,
        title: 'Ready to Go!',
        content: 'Start by choosing a data source. You can build a DAG or upload a CSV.',
        position: 'bottom',
        floating: true,
      },
    ],
  },

  source: {
    id: 'source',
    version: 1,
    completionAction: 'create_pipeline_simulation',
    steps: [
      {
        id: 'source.chooser',
        target: '[data-tour="source-chooser"]',
        title: 'Choose Your Source',
        content: 'Pick "Build a DAG" to define variables and relationships, or upload a CSV file.',
        position: 'bottom',
      },
      {
        id: 'source.add_node',
        target: '[data-tour="add-node-dropdown"]',
        title: 'Add Nodes',
        content: 'Add stochastic (random) or deterministic (formula) nodes to your DAG.',
        position: 'bottom',
      },
      {
        id: 'source.dag_canvas',
        target: '[data-tour="dag-canvas"]',
        title: 'DAG Canvas',
        content: 'Connect nodes by dragging from one to another. Edges define evaluation order.',
        position: 'top',
      },
      {
        id: 'source.preview',
        target: '[data-tour="generate-preview-btn"]',
        title: 'Preview Data',
        content: 'Click Generate Preview to see a sample of your synthetic data.',
        position: 'bottom',
      },
    ],
  },

  transform: {
    id: 'transform',
    version: 1,
    completionAction: 'materialize',
    steps: [
      {
        id: 'transform.formula',
        target: '[data-tour="formula-bar"]',
        title: 'Create a Transformation',
        content: 'Use the formula bar to add new computed columns from your source data.',
        position: 'bottom',
      },
      {
        id: 'transform.recipe',
        target: '[data-tour="recipe-panel"]',
        title: 'Recipe Panel',
        content: 'Your transformation steps build up here. Reorder or remove as needed.',
        position: 'left',
      },
      {
        id: 'transform.materialize',
        target: '[data-tour="materialize-btn"]',
        title: 'Commit Transforms',
        content: 'Click Materialize to apply all transform steps and produce output data.',
        position: 'bottom',
      },
    ],
  },

  model: {
    id: 'model',
    version: 1,
    completionAction: 'fit_model',
    steps: [
      {
        id: 'model.config',
        target: '[data-tour="models-panel"]',
        title: 'Configure Model',
        content: 'Choose a model type, set target and features, then tune parameters.',
        position: 'left',
      },
      {
        id: 'model.fit',
        target: '[data-tour="fit-model-btn"]',
        title: 'Fit the Model',
        content: 'Click Fit Model to train on your data and generate diagnostics.',
        position: 'bottom',
      },
      {
        id: 'model.diagnostics',
        target: '[data-tour="analysis-tabs"]',
        title: 'Explore Diagnostics',
        content: 'View tables, histograms, scatter plots, and model diagnostics here.',
        position: 'right',
      },
    ],
  },

  publish: {
    id: 'publish',
    version: 1,
    completionAction: 'download_csv',
    steps: [
      {
        id: 'publish.export',
        target: '[data-tour="publish-card"]',
        title: 'Export Dataset',
        content: 'Download your synthetic dataset as CSV, Parquet, or JSON.',
        position: 'top',
      },
      {
        id: 'publish.share',
        target: '[data-tour="share-btn"]',
        title: 'Share With Your Team',
        content: 'Generate a shareable link to this version of your project.',
        position: 'bottom',
      },
    ],
  },

  inspector: {
    id: 'inspector',
    version: 1,
    steps: [
      {
        id: 'inspector.hint',
        target: '[data-tour="inspector"]',
        title: 'Inspector',
        content: 'Select any node to configure it here.',
        position: 'left' as const,
      },
    ],
  },
};
