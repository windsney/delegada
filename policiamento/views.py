from django.shortcuts import render, redirect, get_object_or_404
from .models import PontoFixo, EscalaDiaria, CartaoPoliciamento, Policial, ValorHoraCategoria
from datetime import date

# 1. NOVA VIEW: Cadastrar Militares
def cadastrar_policial(request):
    if request.method == "POST":
        nome = request.POST.get('nome_guerra')
        categoria = request.POST.get('categoria')
        if nome and categoria:
            Policial.objects.create(nome_guerra=nome, categoria=categoria)
        return redirect('cadastrar_policial')
        
    policiais = Policial.objects.all()
    categorias = ValorHoraCategoria.CATEGORIAS
    return render(request, 'policiamento/cadastrar_policial.html', {'policiais': policiais, 'categorias': categorias})

# 2. VIEW ATUALIZADA: Painel com cálculo financeiro
def painel_escala(request):
    hoje = date.today()
    escala = EscalaDiaria.objects.filter(data=hoje).first() or EscalaDiaria.objects.order_by('-data').first()
    
    pontos_fixos = PontoFixo.objects.all()
    todos_policiais = Policial.objects.all()
    
    if request.method == "POST":
        data_escala = request.POST.get('data')
        hora_inicio = request.POST.get('hora_inicio')
        hora_fim = request.POST.get('hora_fim')
        
        escala, created = EscalaDiaria.objects.get_or_create(
            data=data_escala,
            defaults={'horario_inicio': hora_inicio, 'horario_fim': hora_fim}
        )
        
        # Atualiza horários se a escala já existia e foi modificada
        if not created:
            escala.horario_inicio = hora_inicio
            escala.horario_fim = hora_fim
            escala.save()
        
        for ponto in pontos_fixos:
            cmd_id = request.POST.get(f'cmd_{ponto.id}')
            mot_id = request.POST.get(f'mot_{ponto.id}')
            pat_id = request.POST.get(f'pat_{ponto.id}')
            
            # Busca as instâncias dos PMs ou deixa None se não selecionado
            cmd = Policial.objects.filter(id=cmd_id).first() if cmd_id else None
            mot = Policial.objects.filter(id=mot_id).first() if mot_id else None
            pat = Policial.objects.filter(id=pat_id).first() if pat_id else None
            
            if cmd or mot or pat:
                CartaoPoliciamento.objects.update_or_create(
                    escala=escala,
                    ponto_fixo=ponto,
                    defaults={'comandante': cmd, 'motorista': mot, 'patrulheiro': pat}
                )
        return redirect('painel_escala')

    # Monta os dados da tabela e calcula os custos dinamicamente
    dados_tabela = []
    custo_total_escala = 0
    horas_turno = escala.total_horas if escala else 0
    
    # Dicionário auxiliar para sabermos o valor/hora atual de cada categoria na listagem
    valores_dict = {v.categoria: float(v.valor_por_hora) for v in ValorHoraCategoria.objects.all()}

    if escala:
        for ponto in pontos_fixos:
            cartao = CartaoPoliciamento.objects.filter(escala=escala, ponto_fixo=ponto).first()
            custo_cartao = cartao.calcular_custo_cartao() if cartao else 0
            custo_total_escala += custo_cartao
            
            dados_tabela.append({
                'ponto': ponto,
                'cartao': cartao,
                'custo_cartao': custo_cartao
            })

    context = {
        'escala': escala,
        'dados_tabela': dados_tabela,
        'policiais': todos_policiais,
        'hoje': hoje.strftime('%Y-%m-%d'),
        'custo_total': custo_total_escala,
        'horas_turno': horas_turno
    }
    return render(request, 'policiamento/painel.html', context)


def visualizacao_escala(request):
    # Busca a escala mais recente cadastrada
    escala = EscalaDiaria.objects.order_by('-data', '-horario_inicio').first()
    
    # Busca os cartões trazendo junto os dados do ponto fixo e dos policiais vinculados
    cartoes = []
    if escala:
        cartoes = CartaoPoliciamento.objects.filter(escala=escala).select_related(
            'ponto_fixo', 'comandante', 'motorista', 'patrulheiro'
        )

    context = {
        'escala': escala,
        'cartoes': cartoes,
    }
    return render(request, 'policiamento/visualizacao.html', context)