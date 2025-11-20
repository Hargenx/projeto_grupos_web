# Organizador de Grupos a partir de Diários em PDF

Aplicação web em --Flask-- que:

- Lê diários de classe em --PDF-- (um arquivo por turma);
- Extrai --matrícula-- e --nome-- dos alunos;
- Permite montar --grupos manualmente por turma--;
- Permite combinar --várias turmas-- e formar grupos mistos entre elas;
- Exporta os grupos formados em --CSV--, --XLSX-- e --JSON--.

Pensado para uso em sala de aula, para facilitar a criação de equipes de trabalho a partir das pautas oficiais.

---

## 📂 Estrutura do projeto

Sugestão de estrutura de pastas:

```text
projeto_grupos_web/
├─ README.md
├─ src/
│  ├─ app.py
│  ├─ templates/
│  │  ├─ base.html
│  │  ├─ index.html
│  │  ├─ grupos.html
│  │  ├─ resultado.html
│  │  ├─ grupos_combinados.html
│  │  └─ resultado_combinado.html
│  ├─ pdfs/(exemplo)
│  │  ├─ TURMA_3001.pdf
│  │  └─ TURMA_3041.pdf
│  └─ data/(gerado)
│     ├─ TURMA_3001/
│     │  ├─ alunos.json
│     │  ├─ grupos.csv
│     │  ├─ grupos.xlsx
│     │  └─ grupos.json
│     ├─ TURMA_3041/
│     │  └─ ...
│     └─ _combos/
│        ├─ TURMA_3001__TURMA_3041/
│        │  ├─ grupos.csv
│        │  ├─ grupos.xlsx
│        │  └─ grupos.json
│        └─ ...
````

- A aplicação considera `src/` como diretório base (por causa do `BASE_DIR = Path(__file__).resolve().parent` no `app.py`).
- Os --PDFs-- ficam em `src/pdfs/`.
- Os dados gerados ficam em `src/data/`:

  - Uma pasta por turma (`data/<TURMA_ID>/`).
  - Combinações de turmas em `data/_combos/<combo_id>/`.

---

## 🧰 Tecnologias utilizadas

- --Python 3.10+-- (testado em 3.11)
- [Flask](https://flask.palletsprojects.com/)
- [pdfplumber](https://github.com/jsvine/pdfplumber) – extração de texto do PDF
- [pandas](https://pandas.pydata.org/) – manipulação de dados e exportações
- [openpyxl](https://openpyxl.readthedocs.io/) – geração de planilhas `.xlsx`
- --Bootstrap 5-- (via CDN) – interface web responsiva

---

## 📦 Instalação

1. Clone ou copie o projeto para sua máquina.

2. (Opcional, mas recomendado) Crie um ambiente virtual:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # ou
   source .venv/bin/activate  # Linux/Mac
   ```

3. Instale as dependências:

   ```bash
   pip install flask pdfplumber pandas openpyxl
   ```

4. Garanta que a estrutura mínima exista dentro de `src/`:

   - `src/app.py`
   - `src/templates/` com os HTMLs
   - `src/pdfs/` (vazia ou com seus PDFs)
   - `src/data/` (será preenchida automaticamente)

---

## 📄 Padrão esperado dos PDFs

O código foi pensado para diários em um formato padronizado, com:

- Cabeçalho da lista de alunos contendo o texto:

  ```text
  Matrícula Nome do Aluno
  ```

- Linhas dos alunos no formato:

  ```text
  <MATRÍCULA> <NOME COMPLETO> ... <colunas de presença: B, P, F, A, "-">
  ```

- Ao final da lista de alunos --ativos--, uma linha com:

  ```text
  ALUNOS EXCLUÍDOS DA TURMA
  ```

A partir disso, o sistema:

- Lê o PDF com `pdfplumber`;
- Percorre as linhas após o cabeçalho;
- Captura:

  - Matrícula (número no início da linha);
  - Nome (até antes das colunas de presença B/P/F/A/-);
- Ignora a seção "ALUNOS EXCLUÍDOS DA TURMA".

Se o layout do PDF mudar muito, pode ser necessário ajustar a função `extrair_alunos_do_pdf` no `app.py`.

---

## ▶️ Como executar

No diretório raiz do projeto:

```bash
python src/app.py
```

Por padrão, o Flask sobe em:

```text
http://127.0.0.1:5000/
```

Abra esse endereço no navegador.

---

## 🧑‍🏫 Fluxo de uso – Turmas individuais

1. Coloque seus diários em PDF dentro de `src/pdfs/`, por exemplo:

   ```text
   src/pdfs/
   ├─ ADS_2025_1_Noite.pdf
   ├─ ADS_2025_1_Manha.pdf
   └─ SI_2025_1_Noite.pdf
   ```

   O --nome do arquivo sem `.pdf`-- será o `turma_id`:

   - `ADS_2025_1_Noite`
   - `ADS_2025_1_Manha`
   - `SI_2025_1_Noite`

2. Acesse a --página inicial-- (`/`):

   - Você verá a lista de turmas detectadas (um PDF = uma turma).
   - Para cada turma aparecem:

     - `turma_id`
     - se o PDF foi encontrado
     - quantos alunos já estão carregados

3. Clique em --“🔄 Atualizar alunos”-- em uma turma:

   - O sistema lê o PDF correspondente;
   - Extrai matrícula e nome;
   - Salva em `data/<TURMA_ID>/alunos.json`.

4. Clique em --“👥 Grupos da turma”--:

   - Leva para `/grupos/<turma_id>`.
   - À esquerda: todos os alunos sem grupo.
   - À direita: cartões de grupos (por padrão, já aparecem alguns, como “Grupo 1”, “Grupo 2”).

5. Para montar grupos:

   - Marque os alunos desejados na tabela da esquerda;
   - Clique em --“Adicionar selecionados”-- no grupo desejado;
   - Os alunos saem da lista de “sem grupo” e entram no grupo escolhido;
   - Você pode:

     - Criar novos grupos (“➕ Novo grupo”);
     - Renomear os grupos;
     - Remover um aluno do grupo (ele volta para a lista à esquerda);
     - Excluir um grupo (todos os alunos do grupo voltam para a lista).

6. Quando terminar, clique em --“💾 Salvar grupos e gerar arquivos”--:

   - O sistema gera:

     - `data/<TURMA_ID>/grupos.csv`
     - `data/<TURMA_ID>/grupos.xlsx`
     - `data/<TURMA_ID>/grupos.json`
   - Redireciona para `/resultado/<turma_id>`, onde:

     - Os grupos são exibidos na tela;
     - Há botões para baixar CSV/XLSX/JSON.

---

## 🔗 Fluxo de uso – Combinação de turmas

Às vezes você quer montar grupos misturando alunos de turmas diferentes (ex.: mesma disciplina em horários diferentes).

1. Na página inicial (`/`):

   - Use as --checkboxes-- na coluna “Combinar” para marcar as turmas que deseja misturar.
   - Clique no botão:

     ```text
     👥 Formar grupos entre turmas selecionadas
     ```

2. Isso leva para `/grupos-combinados?turmas=TurmaA&turmas=TurmaB&...`:

   - À esquerda aparecem --todos os alunos das turmas selecionadas--, com:

     - Matrícula
     - Nome
     - Turma de origem (badge com o `turma_id`)
   - À direita, mesma lógica de grupos:

     - Crie grupos;
     - Adicione alunos de qualquer turma;
     - Remova/ajuste como quiser.

3. Ao salvar:

   - O frontend envia os grupos para `/salvar-grupos-combinados/<combo_id>`.

   - `combo_id` é algo como: `TurmaA__TurmaB__TurmaC`.

   - O sistema gera os arquivos em:

     ```text
     data/_combos/<combo_id>/
       ├─ grupos.csv
       ├─ grupos.xlsx
       └─ grupos.json
     ```

   - E redireciona para `/resultado-combinado/<combo_id>`, onde:

     - Você vê os grupos combinados;
     - Cada aluno aparece com sua turma de origem;
     - Há botões para baixar CSV/XLSX/JSON do combo.

---

## 📑 Formato dos arquivos gerados

### Por turma (`data/<TURMA_ID>/grupos.-`)

Cada linha contém algo como:

- `turma_id`
- `grupo_id`
- `grupo_nome`
- `matricula`
- `nome`

### Por combinação (`data/_combos/<combo_id>/grupos.-`)

Cada linha contém algo como:

- `combo_id`
- `grupo_id`
- `grupo_nome`
- `turma_id` (origem do aluno)
- `matricula`
- `nome`

Isso facilita:

- Fazer chamada de grupos;
- Registrar notas por grupo;
- Importar para outras planilhas/sistemas.

---

## 🛠️ Personalização

Alguns pontos que você pode adaptar no código (`src/app.py`):

- --Padrão de leitura do PDF--
  Função: `extrair_alunos_do_pdf(pdf_path: Path)`

  - Ajustar a linha de detecção do cabeçalho:

    - `"Matrícula Nome do Aluno"`
  - Ajustar a linha de parada:

    - `"ALUNOS EXCLUÍDOS DA TURMA"`
  - Ajustar o regex da matrícula se o formato for diferente.

- --Nomes de pastas e IDs de turmas--
  Hoje, o `turma_id` vem do --nome do arquivo PDF sem a extensão--.
  Você pode mudar a lógica para puxar o nome da turma de dentro do próprio PDF, caso exista essa informação.

- --Estilo da interface--
  Os templates HTML (em `src/templates/`) usam Bootstrap 5 com um tema escuro básico.
  Você pode trocar cores, fontes e layout como quiser.

---

## ❓ Dúvidas e problemas comuns

- --Página inicial não mostra nenhuma turma--
  → Verifique se os PDFs estão dentro de `src/pdfs/` e têm extensão `.pdf`.

- --Nenhum aluno carregado para a turma--
  → Clique em “Atualizar alunos” para aquela turma.
  → Se continuar vazio, provavelmente o layout do PDF está diferente do esperado — revise `extrair_alunos_do_pdf`.

- --Erro ao abrir o app--
  → Confira se as dependências foram instaladas (`flask`, `pdfplumber`, `pandas`, `openpyxl`).
  → Verifique a versão do Python (recomendado 3.10+).

---

## 👤 Autor / Créditos

- --Projeto didático de organização de grupos a partir de pautas em PDF--
- Desenvolvido para facilitar a vida do(a) docente na hora de dividir turmas em equipes de trabalho.
