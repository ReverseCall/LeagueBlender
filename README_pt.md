# LeagueBlender

[![Português](https://img.shields.io/badge/Idioma-Português-green)](README_pt.md)
[![English](https://img.shields.io/badge/Language-English-blue)](README.md)

Import/export toolkit for League of Legends files in Blender.

<p align="center">
  <img src="https://github.com/ReverseCall/static/raw/9950000512368938b3fcf9c7d66d6b66a28fa25e/static/Apresentacao.gif" alt="Plugin presentation"/ width="65%">
</p>

## Sobre o Projeto

LeagueBlender é um plugin para o Blender com foco na importação e exportação de arquivos utilizados pelo **League of Legends**. O objetivo principal deste projeto é permitir a manipulação de **Modelos 3D**, **Armatures**, e outros dados do LoL dentro do anbiente do Blender, inplementando um *workflow* mais moderno e integrado para facilitar a criação de modificações para o jogo

## Marcações

| ✅ | ⚠️ | 🔨 | ❌ | 
|:---:| :---:| :---:|:---:| 
| Suportado | funciona em partes | Em desenvolvimento | Sem planos atuais |

### Suporte de Formatos

A tabela a seguir detalha o status de suporte para importação e exportação dos formatos de arquivo do League of Legends:

| Formato                   | Importação    | Exportação          |
| :------------------------: | :------------: | :------------------: |
| **Skinned Mesh** (`.SKN`)       | ✅ | ✅ |
| **Skeleton** (`.SKL`)           | ✅ | ✅ |
| **Animation** (`.ANM`)          | 🔨 | 🔨 |
| **Static Mesh** (`SCO`)         | 🔨 | 🔨 |
| **Static Mesh Binary** (`.SCB`) | 🔨 | 🔨 |
| **Map Geometry** (`.MAPGEO`)    | ❌ | ❌ |

> [!WARNING]  
> Exportes de **armatures** novos ou modificados não foram testados ainda e podem acabar causando problemas


## Créditos e Agradecimentos

LeagueBlender só se tornou possível graças ao projeto já existente [lol_maya](https://github.com/tarngaina/lol_maya), criado por **tarngaina** & **Crauzer**. Partes da lógica do código foram aproveitadas ou adaptadas para tornar possível a utilização do Blender como principal ferramenta de manipulação de arquivos do League of Legends.

É importante notar que nem todas as funcionalidades presentes no projeto original foram ou serão portadas para o LeagueBlender, como o suporte ao formato `MAPGEO`, que talvez não seja implementado por mim no futuro.

## Instalação

### 1. Baixe o Plugin

Para obter a versão mais recente do LeagueBlender, [clique aqui para baixar](https://github.com/ReverseCall/LeagueBlender/releases/latest).

### 2. Instale no Blender

<details>
<summary>Clique para exibir o guia.</summary>

Siga os passos abaixo para instalar o plugin no Blender:

1.  No Blender, navegue até: `Edit` > `Preferences` > `Add-ons` > `Install...`

2.  Selecione o arquivo `LeagueBlender.zip` do plugin que você baixou.

3.  Após a instalação, ative o *addon* `LeagueBlender`.
</details>

## Como Importar Arquivos

Após a instalação e ativação do plugin, siga estas instruções para importar arquivos:

1.  No Blender, acesse: `File` > `Import`

2.  Você encontrará as seguintes opções de importação:

### Legue Mesh (.skn)

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


> [!TIP]   
> Você pode optar por importar apenas o `.SKL` ao marcar `Import SKL Only` antes de efetivamente importar o seu (.skl + .skn)

## Como Exportar Arquivos

### Exportar uma Mesh (.SKN + .SKL)

* Selecione a malha desejada ou parte da submesh.
* Acesse: `File` > `Export ` > `League Mesh (.skn + .skl)` 
* Escolha o local de destino.
* Clique em Export.

## Preferências do Plugin

<details>

<summary>Clique para exibir.</summary>

As configurações do LeagueBlender podem ser acessadas em: `Edit` > `Preferences` > `Add-ons` > `LeagueBlender`

O plugin atualmente organiza suas configurações da segunte forma:

### Geral

#### Idioma

Permite selecionar o idioma do plugin. Ao escolher um idioma, todos os textos visíveis para o usuário serão exibidos no idioma selecionado.

**Idiomas disponíveis**

- English (Inglês)
- Português (Brasil)

### Preferências do SKN

#### Mesh Topology

Define como a malha será importada para o Blender.

*   **Tris**
    *   Mantém a malha no seu formato original triangulado.
*   **Quad**
    *   Tenta converter automaticamente os triângulos da malha em *quads* para uma topologia mais limpa.

#### Rebuild Seam (BETA)

Esta funcionalidade tenta recriar automaticamente as costuras (*seams*) da malha. O sistema analisa cortes e separações na geometria para identificar regiões onde *seams* provavelmente existiam originalmente.

> [!NOTE]  
> Esta funcionalidade ainda está em fase de desenvolvimento (BETA) e pode gerar resultados inconsistentes dependendo da complexidade do modelo.

#### Gray Mesh by Default

Define o material que será aplicado automaticamente ao importar um arquivo `.SKN`.

*   **Material cinza customizado do plugin**
*   **Material padrão do Blender**

#### Import as Collection (Submeshes)

Define como o modelo será importado para a cena 3D do Blender.

*   **Ativado**
    *   Separa a malha em múltiplos objetos com base nos materiais aplicados ao modelo.
*   **Desativado**
    *   Importa todo o modelo como uma única malha, independentemente da quantidade de materiais utilizados.


#### Merge by Distance

Realiza automaticamente a operação `Merge by Distance` na malha após a importação. Esta ação é útil para:

* Unir malha  para tornar o objeto como algo unico
* Limpar pequenas separações na geometria.
* Melhorar a qualidade geral da geometria importada.

### Preferências do SKL

#### Bone Shape

Permite definir o formato visual dos ossos da *armature* importada. Esta configuração afeta apenas a representação visual dos ossos, sem alterar a estrutura funcional da *armature*.

* **Blender Default**
  * Utiliza o formato padrão de exibição de ossos do Blender.
* **glTF Style**
  * Aplica um estilo visual semelhante ao usado por *armatures* importadas através do formato glTF.

### **Show In Front**

Exibe o *armature* à frente dos demais objetos na *viewport*, facilitando a visualização e a seleção dos ossos mesmo quando estão dentro ou atrás da malha.

## Preferências da cena

### Auto Clip End

Configura o FOV da sua `Sidebar` > `View` > `End` para **10000 m** como padrão ao importar um arquivo `.SKN` ou `.SKL` pela primeira vez para a sua *Cena*.
</details>

## Estado Atual do Projeto

### Funcionalidades Implementadas

*   Importação/Exportação de `SKN`.
*   Importação/Exportação de `SKL`.
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
