# LeagueBlender

[![English](https://img.shields.io/badge/Language-English-blue)](README.md)
[![Português](https://img.shields.io/badge/Idioma-Português-green)](README_pt.md)

Import/export toolkit for League of Legends files in Blender.

<p align="center">
  <img src="https://github.com/ReverseCall/static/raw/9950000512368938b3fcf9c7d66d6b66a28fa25e/static/Apresentacao.gif" alt="Plugin presentation"/ width="65%">
</p>

## About the Project

LeagueBlender is a Blender plugin focused on importing and exporting files used by **League of Legends**. The main goal of this project is to enable manipulation of **3D Models**, **Armatures**, and other LoL data within the Blender environment, implementing a more modern and integrated workflow to facilitate the creation of game modifications.

## Legend

| ✅ | ⚠️ | 🔨 | ❌ |
|:---:|:---:|:---:|:---:|
| Supported | Partially works | In development | No current plans |

### Format Support

The table below details the support status for importing and exporting League of Legends file formats:

| Format | Import | Export |
|:---:|:---:|:---:|
| **Skinned Mesh** (`.SKN`)       | ✅ | ⚠️ |
| **Skeleton** (`.SKL`)           | ✅ | ✅ |
| **Animation** (`.ANM`)          | 🔨 | 🔨 |
| **Static Mesh** (`SCO`)         | 🔨 | 🔨 |
| **Static Mesh Binary** (`.SCB`) | 🔨 | 🔨 |
| **Map Geometry** (`.MAPGEO`)    | ❌ | ❌ |

> [!WARNING]
> Export of new or modified **armatures** has not been tested yet and may cause issues.

## Credits and Acknowledgements

LeagueBlender was only made possible thanks to the existing project [lol_maya](https://github.com/tarngaina/lol_maya), created by **tarngaina** & **Crauzer**. Parts of the code logic were reused or adapted to make Blender viable as the primary tool for manipulating League of Legends files.

It is worth noting that not all features present in the original project have been or will be ported to LeagueBlender, such as support for the `MAPGEO` format, which may not be implemented in the future.

## Installation

### 1. Download the Plugin

To get the latest version of LeagueBlender, [click here to download](https://github.com/ReverseCall/LeagueBlender/releases/latest).

### 2. Install in Blender

Follow the steps below to install the plugin in Blender:

1. In Blender, navigate to: `Edit` > `Preferences` > `Add-ons` > `Install...`
2. Select the `LeagueBlender.zip` file you downloaded.
3. After installation, enable the `LeagueBlender` addon.

## How to Import Files

After installing and enabling the plugin, follow these instructions to import files:

1. In Blender, go to: `File` > `Import`
2. You will find the following import options:

### League Mesh (.skn)

This option imports only the mesh (`.SKN`) of the model. It is recommended when you want to:

* Quickly preview models.
* Edit only the mesh.
* Work without needing an armature.

### League Skeleton (.skl + .skn)

This option imports both the mesh (`.SKN`) and the armature (`.SKL`) together. The plugin automatically reconstructs the complete character structure inside Blender. This is the recommended option for:

* Rigging.
* Animation.
* Exporting.
* Full model editing.

> [!TIP]
> You can choose to import only the `.SKL` by checking `Import SKL Only` before importing your `.skl + .skn` files.

## How to Export Files

### Export a Mesh (.SKN)

* Select the desired mesh.
* Go to: `File` > `Export` > `League Mesh (.skn)`
* Choose the destination folder.
* Click **Export SKN**.

### Export a Skeleton (.SKL)

* Select the desired armature.
* Go to: `File` > `Export` > `League Skeleton (.skl)`
* Choose the destination folder.
* Click **Export SKL**.

## Plugin Preferences

LeagueBlender settings can be accessed at: `Edit` > `Preferences` > `Add-ons` > `LeagueBlender`

The plugin currently organizes its settings into two main categories:

### SKN Preferences

#### Mesh Topology

Defines how the mesh will be imported into Blender.

* **Tris** — Keeps the mesh in its original triangulated format.
* **Quad** — Attempts to automatically convert mesh triangles into quads for a cleaner topology.

#### Rebuild Seam (BETA)

This feature attempts to automatically reconstruct the mesh seams. The system analyzes cuts and separations in the geometry to identify regions where seams likely existed originally.

> [!NOTE]
> This feature is still in development (BETA) and may produce inconsistent results depending on model complexity.

#### Gray Mesh by Default

Defines the material automatically applied when importing a `.SKN` file.

* Plugin's custom gray material
* Blender's default material

#### Merge by Distance

Automatically performs the `Merge by Distance` operation on the mesh after import. This is useful for:

* Merging the mesh to treat it as a single unified object.
* Cleaning up small geometry gaps.
* Improving the overall quality of the imported geometry.

### SKL Preferences

#### Bone Shape

Lets you define the visual shape of the bones in the imported armature. This setting only affects bone display, without changing the armature's functional structure.

* **Blender Default** — Uses Blender's default bone display style.
* **glTF Style** — Applies a visual style similar to armatures imported via the glTF format.

### Show In Front

Displays the armature in front of all other objects in the viewport, making it easier to visualize and select bones even when they are inside or behind the mesh.

## Scene Preferences

### Auto Clip End

Sets the `Sidebar` > `View` > `End` clip distance to **10000 m** by default when importing a `.SKN` or `.SKL` file for the first time into your scene.

## Current Project Status

### Implemented Features

* Import/Export of `SKN`.
* Import/Export of `SKL`.
* Basic mesh reconstruction.
* Quad conversion.
* Armature setup.
* Custom bone shapes.

### In Development

* Improvements to seam reconstruction on import and export.
* Additional support for other League of Legends formats.

> [!NOTE]
> The animation system shown in the presentation video belongs to *LeagueBlender* (2024–2025). The current version of *LeagueBlender* was rewritten with a focus on simplicity, maintainability, and code reduction. The animation system has not yet been reimplemented and will be added in future updates.

## License

This project incorporates and adapts parts of other projects distributed under the GPL license. LeagueBlender is distributed under the [GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.en.html) license.

## Legal Notice

LeagueBlender is an **unofficial** project and has no affiliation with Riot Games. League of Legends and all its intellectual properties belong to Riot Games.