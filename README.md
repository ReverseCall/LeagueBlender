<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0e1a,50:0d2137,100:C89B3C&height=200&section=header&text=LeagueBlender&fontSize=72&fontColor=C89B3C&fontAlignY=38&desc=Import%20%2F%20Export%20League%20of%20Legends%20files%20in%20Blender&descAlignY=64&descSize=18&descFontColor=8ea0b8&animation=fadeIn" />

  <a href="https://git.io/typing-svg"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=16&letterSpacing=3&duration=3000&pause=800&color=C89B3C&center=true&vCenter=true&width=500&lines=Import+LoL+files+into+Blender;Export+your+modifications+back+to+LoL" alt="Typing SVG" /></a>
  ---

  <img src="https://github.com/ReverseCall/static/raw/9950000512368938b3fcf9c7d66d6b66a28fa25e/static/Apresentacao.gif" alt="Plugin presentation" width="75%">

  <br/>
  <br/>

  <a href="README.md">
    <img src="https://img.shields.io/badge/English-0a0e1a?style=for-the-badge&logo=googletranslate&logoColor=C89B3C" />
  </a>
  <a href="README_pt.md">
    <img src="https://img.shields.io/badge/Português-0a0e1a?style=for-the-badge&logo=googletranslate&logoColor=C89B3C" />
  </a>
  <a href="https://github.com/ReverseCall/LeagueBlender/releases/latest">
    <img src="https://img.shields.io/github/v/release/ReverseCall/LeagueBlender?style=for-the-badge&label=Release&color=C89B3C&labelColor=0a0e1a&logoColor=C89B3C">
  </a>
  
</div>

## About the Project

LeagueBlender is a Blender plugin focused on importing and exporting files used by **League of Legends**. The main goal of this project is to enable manipulation of **3D Models**, **Armatures**, and other LoL data within the Blender environment, implementing a more modern and integrated workflow to facilitate the creation of game modifications.

## Legend

| ✅ | ⚠️ | 🔨 | 📂 | ❌ | 
|:---:| :---:| :---:|:---:| :---:| 
| Supported | Partially works | In development | Obsolete | No current plans |

### 📋 Format Support

The table below details the support status for importing and exporting League of Legends file formats:

| Format                   | Import    | Export          |
| :------------------------: | :------------: | :------------------: |
| **Skinned Mesh** (`.SKN`)       | ✅ | ✅ |
| **Skeleton** (`.SKL`)           | ✅ | ✅ |
| **Animation** (`.ANM`)          | 🔨 | 🔨 |
| **Static Mesh** (`SCO`)         | 📂 | 📂 |
| **Static Mesh Binary** (`.SCB`) | ✅ | 🔨 |
| **Map Geometry** (`.MAPGEO`)    | ❌ | ❌ |

> [!WARNING]  
> Export of new or modified **armatures** has not been tested yet and may cause issues.


## Credits and Acknowledgements

LeagueBlender was only made possible thanks to the existing project [lol_maya](https://github.com/tarngaina/lol_maya), created by **tarngaina** & **Crauzer**. Parts of the code logic were reused or adapted to make Blender viable as the primary tool for manipulating League of Legends files.

It is worth noting that not all features present in the original project have been or will be ported to LeagueBlender, such as support for the `MAPGEO` format, which may not be implemented in the future.

## 📥 Installation

### 1. Download the Plugin

<a href="https://github.com/ReverseCall/LeagueBlender/releases/latest">
  <img src="https://img.shields.io/badge/⬇ Download Latest Release-C89B3C?style=for-the-badge&labelColor=0a0e1a" />
</a>

### 2. Install in Blender

<details>
<summary>Click to show the guide.</summary>

Follow the steps below to install the plugin in Blender:

1.  In Blender, navigate to: `Edit` > `Preferences` > `Add-ons` > `Install...`

2.  Select the `LeagueBlender.zip` file you downloaded.

3.  After installation, enable the `LeagueBlender` addon.
</details>

---
<details>
<summary><b>📁 How to Import Files</b></summary>
<br/>
  
After installing and enabling the plugin, follow these instructions to import files:

1.  In Blender, go to: `File` > `Import`

2.  You will find the following import options:

### League Mesh (.skn)

This option imports only the mesh (`.SKN`) of the model. It is recommended when you want to:

* Quickly preview models.
* Edit only the mesh.
* Work without needing an armature.

### League Skeleton (.skl + .skn)

This option imports both the mesh (`.SKN`) and the armature (`.SKL`) together. The plugin automatically reconstructs the complete character structure inside Blender. This is the recommended option for:

*   Rigging.
*   Animation.
*   Exporting.
*   Full model editing.

> You can choose to import only the `.SKL` by checking `Import SKL Only` before importing your `.skl + .skn` files.

### Static Mesh Binary (.scb)

This option allows you to import the mesh (`.scb`) of models. With it, you can perform the following actions:

* Quickly preview models.
* Edit only the mesh.

</details>

<details>
<summary><b>📂 How to Export Files</b></summary>
<br/>
## 

### Export a Mesh (.SKN + .SKL)

* Select the desired mesh or part of the submesh.
* Go to: `File` > `Export` > `League Mesh (.skn + .skl)`
* Choose the destination folder.
* Click Export.

</details>

## Plugin Preferences

LeagueBlender settings can be accessed at: `Edit` > `Preferences` > `Add-ons` > `LeagueBlender`

The plugin currently organizes its settings as follows:

<details>
<summary><b>🔴 Languages</b></summary>

Allows you to select the plugin's language. When a language is chosen, all user-visible text will be displayed in the selected language.

**Available languages**

- English
- Português (Brasil)

</details>


<details>
<summary><b>🔴 SKN / SCB Preferences</b></summary>

| Setting | Option | Description |
|:------|:------------:|:------|
**Mesh Topology** | `Tris`/`Quad` | Keeps the model's original triangles or converts everything to quads for a cleaner mesh |
| **Rebuild Seam (BETA)** | Yes/No | Attempts to automatically reconstruct the mesh seams |
| **Gray Mesh by Default** | Yes/No | Defines the material that will be automatically applied when importing a `SKN` or `SCB` file |
| **Import as Collection (Submeshes)** | Yes/No | Defines whether the model will be imported as submeshes or merged into a single mesh |
| **Merge by Distance** | Enabled/Disabled | When importing a model without reconstructing submeshes, defines whether it will be merged or not |

</details>

<details>
<summary><b>🔴 SKL Preferences</b></summary>

| Setting | Option | Description |
|:------|:------------:|:------|
| **Bone Shape** | `Blender_Default`/`glTF_Style` | Lets you define the visual shape of the bones in the imported armature. This setting only affects bone display, without changing the armature's functional structure. |
| **Show In Front** | Yes/No | Displays the armature in front of all other objects in the viewport, making it easier to visualize and select bones even when they are inside or behind the mesh. |

</details>

<details>
<summary><b>🔴 Scene Preferences</b></summary>

| Setting | Option | Description |
|:------|:------------:|:------|
| **Auto Clip End** | Enabled/Disabled | Sets the `Sidebar` > `View` > `End` clip distance to **10000 m** by default when importing a `.SKN` or `.SKL` file for the first time into your scene. |

</details>

## Current Project Status

### Implemented Features

*   Import/Export of `SKN`.
*   Import/Export of `SKL`.
*   Import of `SCB`.
*   Basic mesh reconstruction.
*   Quad conversion.
*   Armature setup.
*   Custom bone shapes.

### In Development

*   Improvements to seam reconstruction on import and export.
*   Additional support for other League of Legends formats.

> [!NOTE]
> The animation system shown in the presentation video belongs to *LeagueBlender* (2024–2025). The current version of *LeagueBlender* was rewritten with a focus on simplicity, maintainability, and code reduction. The animation system has not yet been reimplemented and will be added in future updates.

## License

This project incorporates and adapts parts of other projects distributed under the GPL license. LeagueBlender is distributed under the [GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.en.html) license.

## Legal Notice

LeagueBlender is an **unofficial** project and has no affiliation with Riot Games. League of Legends and all its intellectual properties belong to Riot Games.

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:C89B3C,50:0d2137,100:0a0e1a&height=120&section=footer&fontSize=14&fontColor=8ea0b8" />

</div>