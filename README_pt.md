<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0e1a,50:0d2137,100:C89B3C&height=200&section=header&text=LeagueBlender&fontSize=72&fontColor=C89B3C&fontAlignY=38&desc=Import%20%2F%20Export%20League%20of%20Legends%20files%20in%20Blender&descAlignY=64&descSize=18&descFontColor=8ea0b8&animation=fadeIn" />

  <a href="https://git.io/typing-svg"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=16&letterSpacing=3&duration=3000&pause=800&color=C89B3C&center=true&vCenter=true&width=500&lines=Importe+arquivos+do+LoL+para+o+Blender;Exporte+suas+modifica%C3%A7%C3%B5es+de+volta+para+LoL" alt="Typing SVG" /></a>
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
    <img src="https://img.shields.io/github/v/release/ReverseCall/LeagueBlender?style=for-the-badge&label=Release&color=C89B3C&labelColor=0a0e1a&logoColor=C89B3C" />
  </a>
  
</div>

## Sobre o Projeto

LeagueBlender é um plugin para o Blender com foco na importação e exportação de arquivos utilizados pelo **League of Legends**. O objetivo principal deste projeto é permitir a manipulação de **Modelos 3D**, **Armatures**, e outros dados do LoL dentro do ambiente do Blender, implementando um *workflow* mais moderno e integrado para facilitar a criação de modificações para o jogo

## Marcações

| ✅ | ⚠️ | 🔨 | 📂 | ❌ | 
|:---:| :---:| :---:|:---:| :---:| 
| Suportado | funciona em partes | Em desenvolvimento | obsoleto | Sem planos atuais |

### 📋 Suporte de Formatos

A tabela a seguir detalha o status de suporte para importação e exportação dos formatos de arquivo do League of Legends:

| Formato                   | Importação    | Exportação          |
| :------------------------: | :------------: | :------------------: |
| **Skinned Mesh** (`.SKN`)       | ✅ | ✅ |
| **Skeleton** (`.SKL`)           | ✅ | ✅ |
| **Animation** (`.ANM`)          | 🔨 | 🔨 |
| **Static Mesh** (`SCO`)         | 📂 | 📂 |
| **Static Mesh Binary** (`.SCB`) | ✅ | 🔨 |
| **Map Geometry** (`.MAPGEO`)    | ❌ | ❌ |

> [!WARNING]  
> Exportes de **armatures** novos ou modificados não foram testados ainda e podem acabar causando problemas


## Créditos e Agradecimentos

LeagueBlender só se tornou possível graças ao projeto já existente [lol_maya](https://github.com/tarngaina/lol_maya), criado por **tarngaina** & **Crauzer**. Partes da lógica do código foram aproveitadas ou adaptadas para tornar possível a utilização do Blender como principal ferramenta de manipulação de arquivos do League of Legends.

É importante notar que nem todas as funcionalidades presentes no projeto original foram ou serão portadas para o LeagueBlender, como o suporte ao formato `MAPGEO`, que talvez não seja implementado por mim no futuro.

## 📥 Instalação

### 1. Baixe o Plugin

<a href="https://github.com/ReverseCall/LeagueBlender/releases/latest">
  <img src="https://img.shields.io/badge/⬇ Download Latest Release-C89B3C?style=for-the-badge&labelColor=0a0e1a" />
</a>

### 2. Instale no Blender

<details>
<summary>Clique para exibir o guia.</summary>

Siga os passos abaixo para instalar o plugin no Blender:

1.  No Blender, navegue até: `Edit` > `Preferences` > `Add-ons` > `Install...`

2.  Selecione o arquivo `LeagueBlender.zip` do plugin que você baixou.

3.  Após a instalação, ative o *addon* `LeagueBlender`.
</details>

---
<details>
<summary><b>📁 Como Importar Arquivos</b></summary>
<br/>
  
Após a instalação e ativação do plugin, siga estas instruções para importar arquivos:

1.  No Blender, acesse: `File` > `Import`

2.  Você encontrará as seguintes opções de importação:

### League Mesh (.skn)

Esta opção permite importar apenas a malha (`.SKN`) do modelo. É recomendada quando você deseja:

* Visualizar modelos rapidamente.
* Editar exclusivamente a malha.
* Trabalhar sem a necessidade de uma *armature*.

### League Skeleton (.skl + .skn)

Esta opção realiza a importação conjunta da malha (`.SKN`) e do *armature* (`.SKL`). O plugin recria automaticamente a estrutura completa do personagem dentro do Blender. É a opção recomendada para:

*   *Rigging*.
*   Animação.
*   Exportação.
*   Edição completa do modelo.
 
> Você pode optar por importar apenas o `.SKL` ao marcar `Import SKL Only` antes de efetivamente importar o seu (.skl + .skn)

### Static Mesh Binary (.scb)

Esta opção permite importar a malha (`.scb`) de modelos. Com ela, é possível realizar as seguintes ações:

* Visualizar modelos rapidamente.
* Editar exclusivamente a malha.

</details>

<details>
<summary><b>📂 Como Exportar Arquivos</b></summary>
<br/>
## 

### Exportar uma Mesh (.SKN + .SKL)

* Selecione a malha desejada ou parte da submesh.
* Acesse: `File` > `Export ` > `League Mesh (.skn + .skl)` 
* Escolha o local de destino.
* Clique em Export.

</details>

## Preferências do Plugin

As configurações do LeagueBlender podem ser acessadas em: `Edit` > `Preferences` > `Add-ons` > `LeagueBlender`

O plugin atualmente organiza suas configurações da seguinte forma:

<details>
<summary><b>🔴 Idiomas</b></summary>

Permite selecionar o idioma do plugin. Ao escolher um idioma, todos os textos visíveis para o usuário serão exibidos no idioma selecionado.

**Idiomas disponíveis**

- English (Inglês)
- Português (Brasil)

</details>


<details>
<summary><b>🔴 Preferências do SKN / SCB</b></summary>

| Configuração | Opção | Descrição |
|:------|:------------:|:------|
**Mesh Topology** | `Tris`/`Quad` | Mantém os triângulos originais do modelo ou converte tudo para quadriláteros deixando a mesh limpa |
| **Rebuild Seam (BETA)** | Sim/Não |  Tenta recriar automaticamente as costuras da malha | 
| **Gray Mesh by Default** | Sim/Não | Define o material que será aplicado automaticamente ao importar um arquivo `SKN` ou `SCB`| 
| **Import as Collection (Submeshes)** | Sim/Não | Define se o modelo sera importado como submeshes ou unido como uma única mesh |
| **Merge by Distance** | Ativo/Desativado | Quando importar um modelo sem recriar as submeshes é possível definir se ele sera unido ou não |

</details>

<details>
<summary><b>🔴 Preferências do SKL</b></summary>

| Configuração | Opção | Descrição |
|:------|:------------:|:------|
| **Bone Shape** | `Blender_Default`/`glTF_Style` | Permite definir o formato visual dos ossos da *armature* importada. Esta configuração afeta apenas a representação visual dos ossos, sem alterar a estrutura funcional da *armature*.|
| **Show In Front** | Sim/Não | Exibe o *armature* à frente dos demais objetos na *viewport*, facilitando a visualização e a seleção dos ossos mesmo quando estão dentro ou atrás da malha.|

</details>

<details>
<summary><b>🔴 Preferências da Cena</b></summary>

| Configuração | Opção | Descrição |
|:------|:------------:|:------|
| **Auto Clip End** | Ativo/Desativado | Configura o FOV da sua `Sidebar` > `View` > `End` para **10000 m** como padrão ao importar um arquivo `.SKN` ou `.SKL` pela primeira vez para a sua *Cena*. |

</details>

## Estado Atual do Projeto

### Funcionalidades Implementadas

*   Importação/Exportação de `SKN`.
*   Importação/Exportação de `SKL`.
*   Importação de `SCB`.
*   Reconstrução básica de *mesh*.
*   Conversão para *quads*.
*   Configuração de *armature*.
*   *Bone shapes* customizados.

### Em Desenvolvimento

*   Melhorias na reconstrução de *seams*. no Importe e Exporte
*   Suporte adicional para outros formatos do League of Legends.

> [!NOTE]
> O sistema de animação mostrado no vídeo de apresentação pertence ao *LeagueBlender* (2024–2025). A versão atual do *LeagueBlender* foi reescrita com foco na simplicidade, facilidade de manutenção e redução de código. O sistema de animação ainda não foi reimplementado e será adicionado em atualizações futuras.

## Licença

Este projeto incorpora e adapta partes de outros projetos distribuídos sob a licença GPL. O LeagueBlender é distribuído sob a licença [GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.en.html).

## Aviso Legal

LeagueBlender é um projeto **não oficial** e não possui afiliação com a Riot Games. League of Legends e todas as suas propriedades intelectuais pertencem à Riot Games.

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:C89B3C,50:0d2137,100:0a0e1a&height=120&section=footer&fontSize=14&fontColor=8ea0b8" />

</div>