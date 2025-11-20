from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any

import pdfplumber
import pandas as pd
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    send_from_directory,
    flash,
)

# ================== CONFIGURAÇÃO BÁSICA ==================

app = Flask(__name__)
app.secret_key = "chave-muito-secreta-mas-simples"  # para mensagens flash

BASE_DIR = Path(__file__).resolve().parent

# Pasta onde ficam TODOS os PDFs (um por turma)
PDFS_DIR = BASE_DIR / "pdfs"
PDFS_DIR.mkdir(exist_ok=True)

# Pasta onde ficam os dados salvos (um subdir por turma)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Pasta específica para combinações de turmas
COMBOS_DIR = DATA_DIR / "_combos"
COMBOS_DIR.mkdir(exist_ok=True)


# ================== MODELO ==================


@dataclass
class Aluno:
    matricula: str
    nome: str


# ================== FUNÇÕES DE CAMINHO POR TURMA / COMBO ==================


def caminhos_turma(turma_id: str):
    """
    Define todos os caminhos relativos a uma turma.
    turma_id = nome do arquivo PDF sem extensão.

    Ex.: pdfs/TURMA_A.pdf  -> turma_id = 'TURMA_A'
    """
    pdf_path = PDFS_DIR / f"{turma_id}.pdf"
    turma_dir = DATA_DIR / turma_id
    turma_dir.mkdir(exist_ok=True)

    alunos_json = turma_dir / "alunos.json"
    session_json = turma_dir / "ultima_sessao_grupos.json"
    export_dir = turma_dir

    return pdf_path, alunos_json, session_json, export_dir


def caminhos_combo(combo_id: str):
    """
    Define caminhos para uma combinação de turmas.
    combo_id = string com turmas unidas por "__", ex.: "TurmaA__TurmaB".
    """
    combo_dir = COMBOS_DIR / combo_id
    combo_dir.mkdir(exist_ok=True)

    session_json = combo_dir / "ultima_sessao_grupos.json"
    export_dir = combo_dir

    return combo_dir, session_json, export_dir


def listar_turmas() -> List[Dict[str, Any]]:
    """
    Lista todas as turmas com base nos PDFs dentro da pasta pdfs/.
    Cada arquivo .pdf vira uma turma.
    """
    turmas = []
    for pdf in PDFS_DIR.glob("*.pdf"):
        turma_id = pdf.stem  # nome do arquivo sem .pdf
        pdf_path, alunos_json, _, _ = caminhos_turma(turma_id)

        if alunos_json.exists():
            with alunos_json.open("r", encoding="utf-8") as f:
                try:
                    dados = json.load(f)
                    qtd_alunos = len(dados)
                except Exception:
                    qtd_alunos = 0
        else:
            qtd_alunos = 0

        turmas.append(
            {
                "turma_id": turma_id,
                "pdf_exists": pdf_path.exists(),
                "qtd_alunos": qtd_alunos,
            }
        )
    return turmas


# ================== PDF -> LISTA DE ALUNOS ==================


def extrair_alunos_do_pdf(pdf_path: Path) -> List[Aluno]:
    """
    Lê o PDF do diário e extrai matrícula + nome dos alunos ativos.

    Premissas:
    - Existe um cabeçalho "Matrícula Nome do Aluno".
    - Depois vêm as linhas com:
        <matricula> <nome completo> ... colunas de presença (B, P, F, A, "-")
    - A seção principal termina em "ALUNOS EXCLUÍDOS DA TURMA".
    """
    alunos: List[Aluno] = []

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF não encontrado em: {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        texto_total = ""
        for pagina in pdf.pages:
            t = pagina.extract_text()
            if t:
                texto_total += t + "\n"

    dentro_lista = False

    for linha in texto_total.splitlines():
        linha = linha.strip()
        if not linha:
            continue

        # Início da tabela
        if linha.startswith("Matrícula Nome do Aluno"):
            dentro_lista = True
            continue

        if not dentro_lista:
            continue

        # Fim da tabela principal (ignoramos excluídos)
        if linha.startswith("ALUNOS EXCLUÍDOS DA TURMA"):
            break

        # Matrícula no começo da linha (entre 6 e 15 dígitos para ser flexível)
        m = re.match(r"^(\d{6,15})\s+(.*)$", linha)
        if not m:
            continue

        matricula = m.group(1)
        resto = m.group(2).strip()
        if not resto:
            continue

        # Separa nome dos marcadores de presença
        tokens = resto.split()
        marcadores_presenca = {"B", "P", "F", "A", "-"}

        nome_tokens: List[str] = []
        for tok in tokens:
            if tok in marcadores_presenca:
                break
            nome_tokens.append(tok)

        if not nome_tokens:
            continue

        nome = " ".join(nome_tokens)
        alunos.append(Aluno(matricula=matricula, nome=nome))

    return alunos


def salvar_alunos_json(alunos: List[Aluno], json_path: Path) -> None:
    dados = [asdict(a) for a in alunos]
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def carregar_alunos_json(json_path: Path) -> List[Aluno]:
    if not json_path.exists():
        return []
    with json_path.open("r", encoding="utf-8") as f:
        dados = json.load(f)
    return [Aluno(matricula=str(d["matricula"]), nome=str(d["nome"])) for d in dados]


# ================== EXPORTAR GRUPOS ==================


def exportar_grupos(linhas: List[Dict[str, Any]], export_dir: Path) -> None:
    """
    Cria:
    - grupos.csv
    - grupos.xlsx
    - grupos.json
    dentro da pasta (export_dir) passada.
    """
    if not linhas:
        return

    df = pd.DataFrame(linhas)

    csv_path = export_dir / "grupos.csv"
    xlsx_path = export_dir / "grupos.xlsx"
    json_path = export_dir / "grupos.json"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(linhas, f, ensure_ascii=False, indent=2)


# ================== ROTAS WEB - TURMAS INDIVIDUAIS ==================


@app.route("/")
def index():
    """
    Tela inicial:
    - Lista as turmas encontradas em pdfs/.
    - Permite selecionar múltiplas turmas para combinação.
    """
    turmas = listar_turmas()
    return render_template("index.html", turmas=turmas)


@app.route("/atualizar-alunos/<turma_id>", methods=["GET", "POST"])
def atualizar_alunos(turma_id):
    """
    Reprocessa o PDF da turma e atualiza o alunos.json correspondente.
    """
    pdf_path, alunos_json_path, _, _ = caminhos_turma(turma_id)

    if not pdf_path.exists():
        flash(f"PDF da turma {turma_id} não encontrado em {pdf_path}", "danger")
        return redirect(url_for("index"))

    try:
        alunos = extrair_alunos_do_pdf(pdf_path)
        salvar_alunos_json(alunos, alunos_json_path)
        flash(
            f"Lista da turma {turma_id} atualizada com {len(alunos)} alunos.", "success"
        )
    except Exception as e:
        flash(f"Erro ao processar o PDF da turma {turma_id}: {e}", "danger")

    return redirect(url_for("index"))


@app.get("/grupos/<turma_id>")
def grupos(turma_id):
    """
    Tela de formação de grupos para uma turma específica.
    """
    _, alunos_json_path, _, _ = caminhos_turma(turma_id)
    alunos = carregar_alunos_json(alunos_json_path)
    if not alunos:
        flash(
            f"Nenhum aluno carregado para a turma {turma_id}. "
            f"Clique em 'Atualizar alunos' na tela inicial.",
            "warning",
        )
        return redirect(url_for("index"))

    alunos_dict = [asdict(a) for a in alunos]
    return render_template("grupos.html", alunos=alunos_dict, turma_id=turma_id)


@app.post("/salvar-grupos/<turma_id>")
def salvar_grupos(turma_id):
    """
    Recebe via JSON a estrutura de grupos montada na interface,
    gera arquivos da turma e salva a sessão.
    """
    _, _, session_json_path, export_dir = caminhos_turma(turma_id)

    data = request.get_json(force=True, silent=False)

    grupos_data = data.get("grupos", [])
    nao_alocados = data.get("nao_alocados", [])

    # Flatten para exportação
    linhas: List[Dict[str, Any]] = []
    for idx, grupo in enumerate(grupos_data, start=1):
        grupo_nome = grupo.get("nome_grupo") or f"Grupo {idx}"
        for membro in grupo.get("membros", []):
            linhas.append(
                {
                    "turma_id": turma_id,
                    "grupo_id": idx,
                    "grupo_nome": grupo_nome,
                    "matricula": membro.get("matricula", ""),
                    "nome": membro.get("nome", ""),
                }
            )

    # Exportar arquivos da turma
    exportar_grupos(linhas, export_dir)

    # Guardar última sessão (para tela de resultado)
    with session_json_path.open("w", encoding="utf-8") as f:
        json.dump(
            {"grupos": grupos_data, "nao_alocados": nao_alocados},
            f,
            ensure_ascii=False,
            indent=2,
        )

    return jsonify({"ok": True, "redirect": url_for("resultado", turma_id=turma_id)})


@app.get("/resultado/<turma_id>")
def resultado(turma_id):
    """
    Mostra os grupos formados na tela e links para baixar os arquivos para aquela turma.
    """
    _, _, session_json_path, _ = caminhos_turma(turma_id)

    grupos_data: List[Dict[str, Any]] = []
    nao_alocados: List[Dict[str, Any]] = []

    if session_json_path.exists():
        with session_json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        grupos_data = data.get("grupos", [])
        nao_alocados = data.get("nao_alocados", [])

    return render_template(
        "resultado.html",
        grupos=grupos_data,
        nao_alocados=nao_alocados,
        turma_id=turma_id,
    )


@app.get("/download/<turma_id>/<path:filename>")
def download(turma_id: str, filename: str):
    """
    Permite baixar arquivos gerados (grupos.csv, grupos.xlsx, grupos.json) da turma.
    """
    _, _, _, export_dir = caminhos_turma(turma_id)
    return send_from_directory(export_dir, filename, as_attachment=True)


# ================== ROTAS WEB - COMBINAÇÃO DE TURMAS ==================


@app.get("/grupos-combinados")
def grupos_combinados():
    """
    Tela de formação de grupos combinando várias turmas.
    Recebe lista de turmas via querystring (?turmas=TurmaA&turmas=TurmaB...).
    """
    turma_ids = request.args.getlist("turmas")
    turma_ids = [t for t in turma_ids if t]
    turma_ids = sorted(set(turma_ids))

    if not turma_ids:
        flash("Selecione pelo menos uma turma para combinar.", "warning")
        return redirect(url_for("index"))

    alunos_comb: List[Dict[str, Any]] = []
    for turma_id in turma_ids:
        _, alunos_json_path, _, _ = caminhos_turma(turma_id)
        alunos = carregar_alunos_json(alunos_json_path)
        for a in alunos:
            d = asdict(a)
            d["turma_id"] = turma_id
            alunos_comb.append(d)

    if not alunos_comb:
        flash("Nenhum aluno encontrado nas turmas selecionadas.", "warning")
        return redirect(url_for("index"))

    combo_id = "__".join(turma_ids)

    return render_template(
        "grupos_combinados.html",
        alunos=alunos_comb,
        turma_ids=turma_ids,
        combo_id=combo_id,
    )


@app.post("/salvar-grupos-combinados/<combo_id>")
def salvar_grupos_combinados(combo_id):
    """
    Recebe via JSON a estrutura de grupos combinados, gera arquivos do combo
    e salva a sessão.
    """
    _, session_json_path, export_dir = caminhos_combo(combo_id)

    data = request.get_json(force=True, silent=False)

    grupos_data = data.get("grupos", [])
    nao_alocados = data.get("nao_alocados", [])

    linhas: List[Dict[str, Any]] = []
    for idx, grupo in enumerate(grupos_data, start=1):
        grupo_nome = grupo.get("nome_grupo") or f"Grupo {idx}"
        for membro in grupo.get("membros", []):
            linhas.append(
                {
                    "combo_id": combo_id,
                    "grupo_id": idx,
                    "grupo_nome": grupo_nome,
                    "turma_id": membro.get("turma_id", ""),
                    "matricula": membro.get("matricula", ""),
                    "nome": membro.get("nome", ""),
                }
            )

    exportar_grupos(linhas, export_dir)

    with session_json_path.open("w", encoding="utf-8") as f:
        json.dump(
            {"grupos": grupos_data, "nao_alocados": nao_alocados},
            f,
            ensure_ascii=False,
            indent=2,
        )

    return jsonify(
        {"ok": True, "redirect": url_for("resultado_combinado", combo_id=combo_id)}
    )


@app.get("/resultado-combinado/<combo_id>")
def resultado_combinado(combo_id):
    """
    Mostra na tela os grupos formados a partir da combinação de turmas.
    """
    _, session_json_path, _ = caminhos_combo(combo_id)

    grupos_data: List[Dict[str, Any]] = []
    nao_alocados: List[Dict[str, Any]] = []

    if session_json_path.exists():
        with session_json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        grupos_data = data.get("grupos", [])
        nao_alocados = data.get("nao_alocados", [])

    turma_ids = combo_id.split("__")

    return render_template(
        "resultado_combinado.html",
        grupos=grupos_data,
        nao_alocados=nao_alocados,
        combo_id=combo_id,
        turma_ids=turma_ids,
    )


@app.get("/download-combo/<combo_id>/<path:filename>")
def download_combo(combo_id: str, filename: str):
    """
    Download de arquivos gerados para uma combinação de turmas.
    """
    _, _, export_dir = caminhos_combo(combo_id)
    return send_from_directory(export_dir, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
