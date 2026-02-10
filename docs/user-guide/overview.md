# User Guide Overview

The KnitPkg User Guide provides a practical, example-driven walkthrough of the most common workflows when using the KnitPkg ecosystem. It is designed to complement the [Concepts](../concepts/overview.md) section by showing how to apply those ideas in real-world scenarios.

This guide is intended to be read sequentially. Each section builds upon the previous one, gradually introducing new features and use cases. Before proceeding, we recommend that you are already familiar with the core concepts of KnitPkg.

---

## What You Will Learn

This guide covers the following topics:

- **Creating Packages**: How to create a new package from scratch.
- **Managing Dependencies**: How to add or remove dependencies in a project.
- **Registry**: How to register a project to the KnitPkg registry.
- **Revisions**: How to release a new version of a project.
- **Creating Projects**: How to create a new MetaTrader project (e.g., Expert Advisor or Indicator).
- **Updates**: How to update a project when a dependency releases a new version.
- **Settings**: How to configure project-specific and global KnitPkg options.

---

## Hands-on Walkthrough

Throughout this guide, we will build and modify real packages and projects. The walkthrough is structured around a set of practical tasks:

### 1. Create a Composite Package: `barhelper`

We will create a new **composite package** called `barhelper`, which provides helper functions for the existing [`bar`](https://forge.mql5.io/DouglasRechia/bar) package. For example, we will implement a `Cross` function that returns `true` or `false` when two `TimeSeries` values cross.

### 2. Extend the `expertdemo` Project

We will update the [`expertdemo`](https://forge.mql5.io/DouglasRechia/expertdemo) project to implement a real trading strategy:

- **Entry condition**: Enter long when `sma1` crosses above `sma2`.
- **Entry filter**: Only enter if `close > sma1 > sma2 > sma3`. This filter can be toggled on or off.
- **Exit condition**: Exit only when `sma1` crosses below `sma2`.
- **Parameter validation**: Ensure that `sma1.period < sma2.period < sma3.period`.

The project will depend on the following packages: [`bar`](https://forge.mql5.io/DouglasRechia/bar), [`calc`](https://forge.mql5.io/DouglasRechia/calc), and `barhelper`.

### 3. Manage Dependencies

We will demonstrate how to:

- Add and remove dependencies using the CLI.
- Use local dependencies during development (e.g., add `barhelper` as a local dependency in `expertdemo`).

### 4. Register a Package

We will publish the new `barhelper` package to the KnitPkg registry using `kp register`.

### 5. Release New Revisions

We will create new versions of the [`bar`](https://forge.mql5.io/DouglasRechia/bar) and [`calc`](https://forge.mql5.io/DouglasRechia/calc) packages. In particular, we will add a new function to [`calc`](https://forge.mql5.io/DouglasRechia/calc) that computes the ATR (Average True Range) indicator.

### 6. Create a New Project

We will create a new indicator project called `atr`, which uses the newly added ATR function from the updated [`calc`](https://forge.mql5.io/DouglasRechia/calc) package.

### 7. Update a Project

We will demonstrate how to update a project when one of its dependencies releases a new version.

### 8. Configure KnitPkg

We will show how to:

- Configure project-specific settings (e.g., compiler paths, data folders).
- Set global options that apply across all projects.

---

## Next Steps

Let’s begin by creating a new package. Continue to [Creating Packages](creating-packages.md).