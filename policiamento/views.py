from django.shortcuts import render, redirect
from .models import PontoFixo, EscalaDiaria, CartaoPoliciamento, Policial, ValorHoraCategoria
from datetime import datetime, date
from django.urls import reverse
from django.http import HttpResponse
from django.db.models import Q
from django.contrib import messages

# Imports do ReportLab para construir o PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def cadastrar_policial(request):
    if request.method == "POST":
        # Coleta os campos obrigatórios
        nome = request.POST.get('nome_guerra')
        categoria = request.POST.get('categoria')
        rgpm = request.POST.get('rgpm')
        cpf = request.POST.get('cpf')
        posto_graduacao = request.POST.get('posto_graduacao')
        endereco = request.POST.get('endereco')
        filiacao = request.POST.get('filiacao')
        naturalidade = request.POST.get('naturalidade')
        data_nascimento = request.POST.get('data_nascimento')
        
        # Coleta os campos opcionais (se vazios, viram None no banco)
        agencia = request.POST.get('agencia') or None
        conta_corrente = request.POST.get('conta_corrente') or None
        telefone = request.POST.get('telefone') or None
        email = request.POST.get('email') or None

        if nome and categoria and rgpm and cpf and posto_graduacao and data_nascimento:
            Policial.objects.create(
                nome_guerra=nome,
                categoria=categoria,
                rgpm=rgpm,
                cpf=cpf,
                posto_graduacao=posto_graduacao,
                endereco=endereco,
                filiacao=filiacao,
                naturalidade=naturalidade,
                data_nascimento=data_nascimento,
                agencia=agencia,
                conta_corrente=conta_corrente,
                telefone=telefone,
                email=email
            )
        return redirect('cadastrar_policial')
        
    policiais = Policial.objects.all()
    categorias = ValorHoraCategoria.CATEGORIAS
    postos = Policial.POSTOS_GRADUACOES
    
    context = {
        'policiais': policiais, 
        'categorias': categorias,
        'postos': postos
    }
    return render(request, 'policiamento/cadastrar_policial.html', context)

# PAINEL ATUALIZADO: Busca e edita por data
def painel_escala(request):
    data_str = request.GET.get('data_busca')
    
    if data_str:
        try:
            data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
            escala = EscalaDiaria.objects.filter(data=data_selecionada).first()
            if not escala:
                escala = EscalaDiaria(data=data_selecionada)
        except ValueError:
            data_selecionada = date.today()
            escala = EscalaDiaria.objects.filter(data=data_selecionada).first()
    else:
        data_selecionada = date.today()
        escala = EscalaDiaria.objects.filter(data=data_selecionada).first() or EscalaDiaria.objects.order_by('-data').first()
        if escala:
            data_selecionada = escala.data
        else:
            escala = EscalaDiaria(data=data_selecionada)

    # Passamos todos os pontos fixos disponíveis para carregar as opções da lista suspensa
    pontos_fixos_disponiveis = PontoFixo.objects.all()
    todos_policiais = Policial.objects.all()
    
    if request.method == "POST":
        data_escala = request.POST.get('data')
        
        # Coleta as listas de dados enviadas do formulário dinâmico
        lista_pontos_id = request.POST.getlist('ponto_id[]')
        lista_hora_inicio = request.POST.getlist('hora_inicio[]')
        lista_hora_fim = request.POST.getlist('hora_fim[]')
        lista_cmd_id = request.POST.getlist('cmd_id[]')
        lista_mot_id = request.POST.getlist('mot_id[]')
        lista_pat_id = request.POST.getlist('pat_id[]')
        
        # ==================== BLOCO DE VALIDAÇÃO DE DUPLICIDADE ====================
        militares_escalados = []
        for i in range(len(lista_pontos_id)):
            cmd = lista_cmd_id[i] if i < len(lista_cmd_id) else ""
            mot = lista_mot_id[i] if i < len(lista_mot_id) else ""
            pat = lista_pat_id[i] if i < len(lista_pat_id) else ""
            
            if cmd: militares_escalados.append(cmd)
            if mot: militares_escalados.append(mot)
            if pat: militares_escalados.append(pat)
            
        if len(militares_escalados) != len(set(militares_escalados)):
            id_duplicado = max(set(militares_escalados), key=militares_escalados.count)
            militar_duplicado = Policial.objects.filter(id=id_duplicado).first()
            messages.error(request, f"Erro: O militar {militar_duplicado} foi inserido em mais de uma vaga/posto no mesmo dia!")
            return redirect(f"{reverse('painel_escala')}?data_busca={data_escala}")
        # ===========================================================================

        # Cria ou obtém a escala do dia
        escala_obj, created = EscalaDiaria.objects.get_or_create(data=data_escala)
        
        # Para evitar cartões órfãos ou duplicados no mesmo ponto, limpamos os cartões antigos do dia
        # e reconstruímos com base nas linhas ativas enviadas pelo operador
        CartaoPoliciamento.objects.filter(escala=escala_obj).delete()
        
        for i in range(len(lista_pontos_id)):
            ponto_id = lista_pontos_id[i]
            if not ponto_id:
                continue  # Pula se a linha não tiver um ponto selecionado
                
            ponto_obj = PontoFixo.objects.filter(id=ponto_id).first()
            if not ponto_obj:
                continue

            h_inicio = lista_hora_inicio[i]
            h_fim = lista_hora_fim[i]
            
            cmd_id = lista_cmd_id[i] if i < len(lista_cmd_id) else None
            mot_id = lista_mot_id[i] if i < len(lista_mot_id) else None
            pat_id = lista_pat_id[i] if i < len(lista_pat_id) else None
            
            cmd = Policial.objects.filter(id=cmd_id).first() if cmd_id else None
            mot = Policial.objects.filter(id=mot_id).first() if mot_id else None
            pat = Policial.objects.filter(id=pat_id).first() if pat_id else None
            
            # Cria o cartão se pelo menos um dado ou horário foi definido
            if ponto_obj and h_inicio and h_fim:
                CartaoPoliciamento.objects.create(
                    escala=escala_obj,
                    ponto_fixo=ponto_obj,
                    comandante=cmd,
                    motorista=mot,
                    patrulheiro=pat,
                    horario_inicio=h_inicio,
                    horario_fim=h_fim
                )
        
        messages.success(request, "Escala salva com sucesso!")
        return redirect(f"{reverse('painel_escala')}?data_busca={data_escala}")

    dados_tabela = []
    custo_total_escala = 0
    valores_dict = {v.categoria: float(v.valor_por_hora) for v in ValorHoraCategoria.objects.all()}

    # Recupera os cartões existentes se houver escala salva
    if escala and escala.pk:
        cartoes = CartaoPoliciamento.objects.filter(escala=escala).select_related('ponto_fixo', 'comandante', 'motorista', 'patrulheiro')
        for cartao in cartoes:
            custo_cartao = 0
            horas = cartao.total_horas
            
            for pm in [cartao.comandante, cartao.motorista, cartao.patrulheiro]:
                if pm:
                    valor_hora_pm = valores_dict.get(pm.categoria, 0.0)
                    custo_cartao += (horas * valor_hora_pm)
                    
            custo_total_escala += custo_cartao
            
            dados_tabela.append({
                'ponto': cartao.ponto_fixo,
                'cartao': cartao,
                'custo_cartao': custo_cartao
            })

    context = {
        'escala': escala,
        'data_selecionada': data_selecionada.strftime('%Y-%m-%d'),
        'dados_tabela': dados_tabela,
        'pontos_fixos': pontos_fixos_disponiveis, # Passado para gerar as opções no template
        'policiais': todos_policiais,
        'custo_total': custo_total_escala,
    }
    return render(request, 'policiamento/painel.html', context)


# VISUALIZAÇÃO ATUALIZADA: Histórico e busca para os policiais
def visualizacao_escala(request):
    data_str = request.GET.get('data_busca')
    
    if data_str:
        try:
            data_busca = datetime.strptime(data_str, '%Y-%m-%d').date()
            escala = EscalaDiaria.objects.filter(data=data_busca).first()
        except ValueError:
            escala = None
    else:
        # Padrão: Mostra a escala mais recente
        escala = EscalaDiaria.objects.order_by('-data').first()

    cartoes = []
    if escala:
        cartoes = CartaoPoliciamento.objects.filter(escala=escala).select_related(
            'ponto_fixo', 'comandante', 'motorista', 'patrulheiro'
        ).order_by('horario_inicio')

    # Lista todas as datas que já possuem escalas criadas no sistema para o menu lateral/histórico
    historico_escalas = EscalaDiaria.objects.order_by('-data')

    context = {
        'escala': escala,
        'cartoes': cartoes,
        'historico': historico_escalas,
        'data_buscada': data_str if data_str else '',
    }
    return render(request, 'policiamento/visualizacao.html', context)

def gerar_pdf_fichas_ponto(request):
    # 1. Captura o mês e ano do filtro (Padrão: mês/ano atual)
    hoje = date.today()
    mes = int(request.GET.get('mes', hoje.month))
    ano = int(request.GET.get('ano', hoje.year))

    # 2. Busca todos os cartões de policiamento do mês/ano filtrado
    cartoes_mes = CartaoPoliciamento.objects.filter(
        escala__data__month=mes,
        escala__data__year=ano
    ).select_related('escala', 'ponto_fixo', 'comandante', 'motorista', 'patrulheiro')

    # 3. Agrupa os serviços por Policial individual
    ficha_policiais = {}
    
    for cartao in cartoes_mes:
        equipe = [cartao.comandante, cartao.motorista, cartao.patrulheiro]
        for pm in equipe:
            if pm: 
                if pm not in ficha_policiais:
                    ficha_policiais[pm] = []
                ficha_policiais[pm].append(cartao)

    # 4. Configuração da resposta HTTP para retornar um PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="fichas_ponto_{mes}_{ano}.pdf"'

    # 5. Criação do documento PDF usando ReportLab
    doc = SimpleDocTemplate(
        response, 
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Estilos customizados para o documento oficial
    estilo_titulo = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=14, leading=16, alignment=1, textColor=colors.HexColor('#1e3a8a'))
    estilo_sub = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10, leading=12, alignment=1, textColor=colors.HexColor('#475569'))
    estilo_corpo = ParagraphStyle('Corpo', parent=styles['Normal'], fontSize=9, leading=13)
    estilo_tabela_header = ParagraphStyle('TabHeader', parent=styles['Normal'], fontSize=9, leading=11, fontName='Helvetica-Bold', textColor=colors.white)
    estilo_tabela_celula = ParagraphStyle('TabCell', parent=styles['Normal'], fontSize=9, leading=11)

    elements = []

    # 6. Montagem da Ficha de Ponto de cada Policial
    for pm, lista_cartoes in ficha_policiais.items():
        
        # Cabeçalho da Folha de Ponto
        elements.append(Paragraph("POLÍCIA MILITAR DE MATO GROSSO", estilo_titulo))
        elements.append(Paragraph("COMANDO REGIONAL DE RONDONÓPOLIS", estilo_sub))
        elements.append(Paragraph(f"<b>FICHA DE PONTO INDIVIDUAL - ATIVIDADE DELEGADA ({mes:02d}/{ano})</b>", estilo_sub))
        elements.append(Spacer(1, 12))

        # ================= NOVO: TABELA DE DADOS CADASTRAIS DO MILITAR =================
        # Criamos uma mini tabela estruturada em duas colunas para comportar as novas informações
        dados_cadastrais = [
            [
                Paragraph(f"<b>Nome Completo:</b> {pm.nome_guerra}", estilo_corpo),
                Paragraph(f"<b>Posto / Graduação:</b> {pm.get_posto_graduacao_display()}", estilo_corpo)
            ],
            [
                Paragraph(f"<b>RGPM:</b> {pm.rgpm}", estilo_corpo),
                Paragraph(f"<b>CPF:</b> {pm.cpf}", estilo_corpo)
            ],
            [
                Paragraph(f"<b>Data de Nasc.:</b> {pm.data_nascimento.strftime('%d/%m/%Y')}", estilo_corpo),
                Paragraph(f"<b>Naturalidade:</b> {pm.naturalidade}", estilo_corpo)
            ],
            [
                Paragraph(f"<b>Filiação:</b> {pm.filiacao}", estilo_corpo),
                Paragraph(f"<b>Telefone:</b> {pm.telefone or '---'}", estilo_corpo)
            ],
            [
                Paragraph(f"<b>Endereço:</b> {pm.endereco}", estilo_corpo),
                Paragraph(f"<b>E-mail:</b> {pm.email or '---'}", estilo_corpo)
            ],
            [
                Paragraph(f"<b>Banco/Agência:</b> {pm.agencia or '---'}", estilo_corpo),
                Paragraph(f"<b>Conta Corrente:</b> {pm.conta_corrente or '---'}", estilo_corpo)
            ],
            [
                Paragraph(f"<b>Categoria de Custo:</b> {pm.get_categoria_display()}", estilo_corpo),
                Paragraph("", estilo_corpo) # Célula vazia para fechar a linha
            ]
        ]
        
        tabela_dados = Table(dados_cadastrais, colWidths=[265, 265])
        tabela_dados.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        
        elements.append(tabela_dados)
        elements.append(Spacer(1, 15))
        # =================================
        # ===============================================================================

        # Tabela de Dias Trabalhados
        dados_tabela = [[
            Paragraph("Data", estilo_tabela_header),
            Paragraph("Ponto Fixo / Posto", estilo_tabela_header),
            Paragraph("Início", estilo_tabela_header),
            Paragraph("Fim", estilo_tabela_header),
            Paragraph("Horas", estilo_tabela_header),
            Paragraph("Valor (R$)", estilo_tabela_header)
        ]]

        total_horas_militar = 0
        total_receber_militar = 0

        lista_cartoes_ordenados = sorted(lista_cartoes, key=lambda c: c.escala.data)

        valores_dict = {v.categoria: float(v.valor_por_hora) for v in ValorHoraCategoria.objects.all()}

        for cartao in lista_cartoes_ordenados:
            horas = cartao.total_horas 
            
            valor_hora = valores_dict.get(pm.categoria, 0.0)
            custo_individual = horas * valor_hora
            
            total_horas_militar += horas
            total_receber_militar += custo_individual

            dados_tabela.append([
                Paragraph(cartao.escala.data.strftime('%d/%m/%Y'), estilo_tabela_celula),
                Paragraph(cartao.ponto_fixo.nome, estilo_tabela_celula),
                Paragraph(cartao.horario_inicio.strftime('%H:%M'), estilo_tabela_celula),
                Paragraph(cartao.horario_fim.strftime('%H:%M'), estilo_tabela_celula),
                Paragraph(f"{horas:.1f}h", estilo_tabela_celula),
                Paragraph(f"R$ {custo_individual:.2f}", estilo_tabela_celula)
            ])

        # Linha de Totais do Militar
        dados_tabela.append([
            Paragraph("<b>TOTAL DO MÊS</b>", estilo_tabela_celula),
            "", "", "",
            Paragraph(f"<b>{total_horas_militar:.1f}h</b>", estilo_tabela_celula),
            Paragraph(f"<b>R$ {total_receber_militar:.2f}</b>", estilo_tabela_celula)
        ])

        tabela = Table(dados_tabela, colWidths=[65, 180, 50, 50, 50, 85])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor('#1e3a8a')),
            ('SPAN', (0, -1), (3, -1)),
        ]))
        
        elements.append(tabela)
        elements.append(Spacer(1, 35))

        # Campos de assinatura regulamentares
        dados_assinatura = [
            [
                Paragraph("_______________________________________<br/>Assinatura do Militar Escalado", estilo_sub),
                Paragraph("_______________________________________<br/>Gestor do Comando Regional", estilo_sub)
            ]
        ]
        tabela_ass = Table(dados_assinatura, colWidths=[265, 265])
        tabela_ass.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
        elements.append(tabela_ass)

        elements.append(PageBreak())

    if elements:
        elements.pop()

    doc.build(elements)
    return response