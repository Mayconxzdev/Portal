import pytest
import os
import uuid
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.stock import (
    StockCatalogImportRun,
    StockCatalogTreeNode,
    StockCatalogItem,
    StockCatalogSupplier,
    StockCatalogOffer,
    StockCatalogPriceHistory,
    StockCatalogCybersulProduct,
    StockCatalogLink,
    StockCatalogSearchIndex
)
from app.models.audit_log import AuditLog
from app.models.event_log import EventLog
from app.models.user import User
from app.models.role import Role
from app.modules.stock.service import StockCatalogService
from app.modules.stock.parser import ComprasNovaParser
from app.modules.stock.cybersul import CybersulImporter
from app.modules.stock.measure_utils import measures_equivalent, normalize_measure, strip_measurements_from_name

FIXTURES_DIR = Path(__file__).parent / "fixtures"
COMPRAS_NOVA_PATH = os.getenv("PORTAL_TEST_COMPRAS_NOVA_PATH", str(FIXTURES_DIR / "compras-nova.xlsx"))
CYBERSUL_PATH = os.getenv("PORTAL_TEST_CYBERSUL_PATH", str(FIXTURES_DIR / "cybersul.xlsx"))
UNIFIED_PATH = os.getenv(
    "PORTAL_TEST_UNIFIED_CATALOG_PATH",
    str(FIXTURES_DIR / "catalogo-unificado.xlsx"),
)


def require_real_stock_workbook(path: str, label: str):
    if not os.path.exists(path):
        pytest.skip(
            f"{label} nao encontrada em {path}. "
            "Defina a variavel de ambiente correspondente para rodar este teste com a planilha real."
        )


def test_measure_normalizer_equates_imperial_and_metric_pair():
    imperial = normalize_measure('1.1/2" x 1/8"')
    metric = normalize_measure("38,1 mm x 3,18 mm")

    assert imperial.kind == "complete"
    assert metric.kind == "complete"
    assert imperial.canonical_key == metric.canonical_key
    assert imperial.display == "38,1 x 3,18 mm"
    assert measures_equivalent('1 1/2" x 1/8"', "38.1 mm x 3.18 mm")


def test_measure_normalizer_accepts_mixed_fraction_forms_and_curly_quotes():
    values = [
        '1.1/2" x 1/8"',
        '1 1/2" x 1/8"',
        '1-1/2” x 1/8”',
        '1½" x 1/8"',
    ]
    keys = {normalize_measure(value).canonical_key for value in values}

    assert keys == {"mm:38.10x3.18"}


def test_measure_normalizer_marks_partial_measure_as_thickness():
    partial = normalize_measure('3/16"')

    assert partial.kind == "partial"
    assert partial.canonical_key == "partial:4.76"
    assert partial.display == "Espessura: 4,76 mm"

@pytest.fixture(autouse=True)
def setup_stock_module(db: Session):
    # Cadastrar módulo stock e purchases para que as permissões funcionem
    from app.models.module import Module
    from app.models.user_module_access import UserModuleAccess
    
    # Adicionar módulo stock se não existir
    stock_mod = db.query(Module).filter(Module.code == "stock").first()
    if not stock_mod:
        stock_mod = Module(name="Estoque & Catálogo", code="stock", is_active=True, is_restricted=False)
        db.add(stock_mod)
        
    purch_mod = db.query(Module).filter(Module.code == "purchases").first()
    if not purch_mod:
        purch_mod = Module(name="Compras", code="purchases", is_active=True, is_restricted=False)
        db.add(purch_mod)
        
    db.commit()


def create_minimal_stock_item(db: Session):
    run = StockCatalogImportRun(
        source_type="QA",
        source_path="qa-fixture",
        source_filename="qa-fixture.xlsx",
        source_hash=str(uuid.uuid4()).replace("-", ""),
        status="SUCCESS",
        total_rows=1,
        total_items=2,
        total_offers=2,
    )
    db.add(run)
    db.flush()

    supplier = StockCatalogSupplier(
        name="Fornecedor QA",
        normalized_name=f"fornecedor qa {uuid.uuid4()}",
        email="qa.fornecedor@vesper.local",
        phone="(00) 0000-0000",
        active=True,
    )
    other_supplier = StockCatalogSupplier(
        name="Outro Fornecedor QA",
        normalized_name=f"outro fornecedor qa {uuid.uuid4()}",
        email="outro.qa@vesper.local",
        active=True,
    )
    db.add_all([supplier, other_supplier])
    db.flush()

    item = StockCatalogItem(
        import_run_id=run.id,
        source_sheet="QA",
        display_name="Item QA para atualizacao de preco",
        base_name="Item QA",
        normalized_name="item qa para atualizacao de preco",
        variation_label="10 mm",
        normalized_measure="10 mm",
        canonical_measure_key="mm:10.00",
        measure_display="10 mm",
        measure_kind="partial",
        identity_hash=str(uuid.uuid4()).replace("-", ""),
        canonical_category="qa",
        canonical_category_display="QA",
        visibility_scope="COMMON",
        active=True,
        is_parser_junk=False,
    )
    other_item = StockCatalogItem(
        import_run_id=run.id,
        source_sheet="QA",
        display_name="Outro item QA",
        base_name="Outro item QA",
        normalized_name="outro item qa",
        identity_hash=str(uuid.uuid4()).replace("-", ""),
        canonical_category="qa",
        canonical_category_display="QA",
        visibility_scope="COMMON",
        active=True,
        is_parser_junk=False,
    )
    db.add_all([item, other_item])
    db.flush()

    offer = StockCatalogOffer(
        item_id=item.id,
        supplier_id=supplier.id,
        import_run_id=run.id,
        source_sheet="QA",
        source_row=1,
        price=25.0,
        price_raw="R$ 25,00",
        final_value=25.0,
        contact_email=supplier.email,
        unit="un",
        is_current=True,
    )
    other_offer = StockCatalogOffer(
        item_id=other_item.id,
        supplier_id=other_supplier.id,
        import_run_id=run.id,
        source_sheet="QA",
        source_row=2,
        price=99.0,
        price_raw="R$ 99,00",
        final_value=99.0,
        contact_email=other_supplier.email,
        unit="un",
        is_current=True,
    )
    search_index = StockCatalogSearchIndex(
        item_id=item.id,
        search_text="Item QA para atualizacao de preco Fornecedor QA 10 mm",
        normalized_search_text="item qa para atualizacao de preco fornecedor qa 10 mm",
        tokens_json=["item", "qa", "preco", "fornecedor"],
        supplier_names=[supplier.name],
        source_sheet="QA",
        family_path="QA > Item QA",
        last_price=25.0,
        last_supplier=supplier.name,
    )
    db.add_all([offer, other_offer, search_index])
    db.commit()
    return item, offer, other_offer


def create_search_catalog_fixture(db: Session):
    run = StockCatalogImportRun(
        source_type="QA_SEARCH",
        source_path="qa-search-fixture",
        source_filename="qa-search-fixture.xlsx",
        source_hash=str(uuid.uuid4()).replace("-", ""),
        status="SUCCESS",
        total_rows=6,
        total_items=6,
        total_offers=6,
    )
    db.add(run)
    db.flush()

    fam = StockCatalogSupplier(
        name="FAM",
        normalized_name=f"fam {uuid.uuid4()}",
        active=True,
    )
    guarnital = StockCatalogSupplier(
        name="GUARNITAL",
        normalized_name=f"guarnital {uuid.uuid4()}",
        active=True,
    )
    db.add_all([fam, guarnital])
    db.flush()

    def add_fixture_item(display_name, base_name, variation, spec, supplier, price, search_text):
        item = StockCatalogItem(
            import_run_id=run.id,
            source_sheet="QA Busca",
            display_name=display_name,
            base_name=base_name,
            normalized_name=display_name.lower(),
            variation_label=variation,
            normalized_measure=spec,
            specification_text=spec,
            measure_display=spec,
            identity_hash=str(uuid.uuid4()).replace("-", ""),
            canonical_category="qa-busca",
            canonical_category_display="QA Busca",
            visibility_scope="COMMON",
            active=True,
            is_parser_junk=False,
        )
        db.add(item)
        db.flush()

        offer = StockCatalogOffer(
            item_id=item.id,
            supplier_id=supplier.id,
            import_run_id=run.id,
            source_sheet="QA Busca",
            source_row=1,
            price=price,
            price_raw=f"R$ {price:.2f}",
            final_value=price,
            unit="un",
            is_current=True,
        )
        index = StockCatalogSearchIndex(
            item_id=item.id,
            search_text=search_text,
            normalized_search_text=search_text.lower(),
            tokens_json=search_text.lower().split(),
            supplier_names=[supplier.name],
            source_sheet="QA Busca",
            family_path="QA Busca > Materiais",
            last_price=price,
            last_supplier=supplier.name,
        )
        db.add_all([offer, index])
        return item

    tube_base = "Tubo Aco Redondo Polido 1020 c/ Costura"
    add_fixture_item(f"{tube_base} - 3/8", tube_base, '3/8"', "9,53 mm", fam, 30.69, f"{tube_base} 3/8 9,53 mm fam tubo aco redondo")
    add_fixture_item(f"{tube_base} - 1/2", tube_base, '1/2"', "12,70 mm", fam, 40.10, f"{tube_base} 1/2 12,70 mm fam tubo aco redondo")
    add_fixture_item(f"{tube_base} - 3/4", tube_base, '3/4"', "19,05 mm", fam, 48.90, f"{tube_base} 3/4 19,05 mm fam tubo aco redondo")
    add_fixture_item(f"{tube_base} - 1", tube_base, '1"', "25,40 mm", fam, 58.40, f"{tube_base} 1 25,40 mm fam tubo aco redondo")
    add_fixture_item(f"{tube_base} - 1.1/2", tube_base, '1.1/2"', "38,10 mm", fam, 70.50, f"{tube_base} 1.1/2 38,10 mm fam tubo aco redondo")
    add_fixture_item("Papel Velumoid GUARNITAL AM 3/32", "Papel Velumoid GUARNITAL AM", '3/32"', "2,38 mm", guarnital, 12.30, "papel velumoid guarnital am 3/32 2,38 mm")

    db.commit()

def test_sheet_parser_real_execution(db: Session):
    """
    Testa o processamento real da planilha Compras Nova .xlsx por árvore visual.
    """
    require_real_stock_workbook(COMPRAS_NOVA_PATH, "Planilha Compras Nova .xlsx")
    
    # Criar um usuário admin para simular a autoria da sincronização
    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    admin_user = db.query(User).filter(User.role_id == admin_role.id).first()
    
    # Rodar sincronização
    run = ComprasNovaParser.parse_workbook(COMPRAS_NOVA_PATH, db, user_id=admin_user.id)
    
    assert run.status == "SUCCESS"
    assert run.total_items > 0
    assert run.total_offers > 0

    # 1. CASO OBRIGATÓRIO: TUBO AÇO REDONDO (5 variações sob o mesmo produto)
    # Procurar os tubos importados
    tubos = db.query(StockCatalogItem).filter(
        StockCatalogItem.base_name.like("%Tubo Aço Redondo Polido 1020 c/ Costura%")
    ).all()
    
    # Devem ser exatamente 5 variações criadas
    assert len(tubos) == 5, f"Foram criados {len(tubos)} tubos em vez de 5!"
    
    # Verificar os detalhes das variações de 3/8" e 1.1/2"
    tubo_3_8 = next((t for t in tubos if t.variation_label and "3/8" in t.variation_label), None)
    assert tubo_3_8 is not None, "Variação de 3/8\" não encontrada para Tubo Aço Redondo!"
    assert tubo_3_8.specification_text == "9,53 mm"
    
    offers_3_8 = db.query(StockCatalogOffer).filter(StockCatalogOffer.item_id == tubo_3_8.id).all()
    assert len(offers_3_8) == 1
    assert float(offers_3_8[0].price) == 30.69
    assert offers_3_8[0].supplier.name == "FAM"
    
    tubo_1_1_2 = next((t for t in tubos if t.variation_label and "1.1/2" in t.variation_label), None)
    assert tubo_1_1_2 is not None, "Variação de 1.1/2\" não encontrada para Tubo Aço Redondo!"
    assert tubo_1_1_2.specification_text == "38,1 mm"
    
    offers_1_1_2 = db.query(StockCatalogOffer).filter(StockCatalogOffer.item_id == tubo_1_1_2.id).all()
    assert len(offers_1_1_2) == 1
    assert float(offers_1_1_2[0].price) == 70.50
    assert offers_1_1_2[0].supplier.name == "FAM"

    # 2. CASO OBRIGATÓRIO: MAT. ELÉTRICO EX
    # Verificar o Interruptor Margirus Blindado (Bipolar e Tripolar)
    int_bipolar = db.query(StockCatalogItem).filter(
        StockCatalogItem.base_name.like("%Interruptor Margirus Blindado%"),
        StockCatalogItem.variation_label.like("%Bipolar%")
    ).first()
    assert int_bipolar is not None, "Interruptor Margirus Blindado Bipolar não encontrado!"
    
    int_tripolar = db.query(StockCatalogItem).filter(
        StockCatalogItem.base_name.like("%Interruptor Margirus Blindado%"),
        StockCatalogItem.variation_label.like("%Tripolar%")
    ).first()
    assert int_tripolar is not None, "Interruptor Margirus Blindado Tripolar não encontrado!"
    
    # 3. CASO OBRIGATÓRIO: CONEXÕES ALTA PRESSÃO (Atuador como família isolada)
    # O Atuador não deve estar subordinado a "Alta Pressão - Peças"
    atuador_nodes = db.query(StockCatalogTreeNode).filter(
        StockCatalogTreeNode.node_type == "family",
        StockCatalogTreeNode.title == "ATUADOR"
    ).all()
    assert len(atuador_nodes) > 0, "Família 'ATUADOR' não foi encontrada!"
    
    # Atuadores específicos devem existir
    da100 = db.query(StockCatalogItem).filter(StockCatalogItem.base_name.like("%ATUADOR PNEUMATICO DE DUPLA ACAO - DA100%")).first()
    if not da100:
        da100 = db.query(StockCatalogItem).filter(StockCatalogItem.display_name.like("%DA100%")).first()
    assert da100 is not None, "Atuador DA100 não encontrado!"

    # 4. CASO OBRIGATÓRIO: PAPEL VELUMOID (Guarnital AM 3/32 e Guarnital AM 1/8 separados)
    velumoid_items = db.query(StockCatalogItem).filter(
        StockCatalogItem.base_name.like("%Papel Velumoid%")
    ).all()
    if not velumoid_items:
        velumoid_items = db.query(StockCatalogItem).filter(
            StockCatalogItem.display_name.like("%Guarnital%")
        ).all()
    assert len(velumoid_items) >= 2, "Itens de Papel Velumoid (Guarnital) não foram separados!"

    # 5. CASO OBRIGATÓRIO: BICO / CONEMANG
    # O fornecedor é Conemang Comercio
    conemang = db.query(StockCatalogSupplier).filter(
        StockCatalogSupplier.normalized_name == "conemang comercio"
    ).first()
    assert conemang is not None, "Fornecedor 'Conemang Comercio' não foi devidamente mapeado no banco!"

def test_cybersul_importer_real_execution(db: Session):
    """
    Testa a importação da base de dados do Cybersul cybersul-codigo.xlsx e seus vínculos.
    """
    require_real_stock_workbook(COMPRAS_NOVA_PATH, "Planilha Compras Nova .xlsx")
    require_real_stock_workbook(CYBERSUL_PATH, "Planilha cybersul-codigo.xlsx")
    
    # Criar um usuário admin para simular a autoria da sincronização
    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    admin_user = db.query(User).filter(User.role_id == admin_role.id).first()
    
    # Rodar sincronizações (sincroniza Compras primeiro para podermos testar o pareamento de links)
    ComprasNovaParser.parse_workbook(COMPRAS_NOVA_PATH, db, user_id=admin_user.id)
    run_cyber = CybersulImporter.import_products(CYBERSUL_PATH, db, user_id=admin_user.id)
    
    assert run_cyber.status == "SUCCESS"
    assert run_cyber.total_items > 0
    
    # Verificar importação de saldos e dados cadastrais
    plug_stek = db.query(StockCatalogCybersulProduct).filter(
        StockCatalogCybersulProduct.cybersul_code == "VPC10230037"
    ).first()
    assert plug_stek is not None, "Produto 'VPC10230037' do Cybersul não foi importado!"
    assert float(plug_stek.balance_vesper) == 5.0
    assert float(plug_stek.balance_ventrio) == 0.0
    assert float(plug_stek.balance_total) == 5.0
    
    # Verificar se algum link/vínculo automático foi gerado
    links = db.query(StockCatalogLink).all()
    assert len(links) > 0, "Nenhum vínculo automático Cybersul x Compras Nova foi criado!"

def test_catalog_search(db: Session):
    """
    Valida a busca tolerante do catalogo para termos obrigatorios sem reler Excel no runtime.
    """
    create_search_catalog_fixture(db)

    # Buscar: Tubo Aco Redondo (Encontra as 5 variacoes)
    res_tubo = StockCatalogService.search_catalog(db, "Tubo Aco Redondo")
    assert len(res_tubo) >= 5

    # Buscar: 9,53 mm (Encontra a variacao de 3/8")
    res_medida = StockCatalogService.search_catalog(db, "9,53 mm")
    assert any("3/8" in r["display_name"] for r in res_medida)

    # Buscar: FAM (Encontra ofertas do fornecedor FAM)
    res_fam = StockCatalogService.search_catalog(db, "FAM")
    assert any(r["last_supplier"] == "FAM" for r in res_fam)

    # Buscar: Papel Velumoid GUARNITAL AM 3/32
    res_vel = StockCatalogService.search_catalog(db, "GUARNITAL AM 3/32")
    assert len(res_vel) > 0
    # O item deve ter "3/32" no display_name (pode nao ser o primeiro resultado)
    assert any("3/32" in r["display_name"] for r in res_vel), \
        f"Nenhum resultado de 'GUARNITAL AM 3/32' contem '3/32' no display_name. " \
        f"Resultados: {[r['display_name'] for r in res_vel[:5]]}"


def test_price_update_and_audit(db: Session):
    """
    Testa o fluxo de atualização manual de preços e auditoria de histórico.
    """
    # Configurar dados base
    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    admin_user = db.query(User).filter(User.role_id == admin_role.id).first()
    item, offer, _ = create_minimal_stock_item(db)
    
    assert item is not None
    assert offer is not None
    
    old_price = float(offer.price) if offer.price else 0.0
    new_price = old_price + 10.0
    
    # Executar atualização manual
    res = StockCatalogService.update_item_price(
        db=db,
        item_id=item.id,
        supplier_id=offer.supplier_id,
        new_price=new_price,
        notes="Preço reajustado por negociação direta",
        user_id=admin_user.id
    )
    
    assert res["new_price"] == new_price
    
    # Verificar se uma nova oferta corrente foi gerada
    new_offer = db.query(StockCatalogOffer).filter(
        StockCatalogOffer.item_id == item.id,
        StockCatalogOffer.supplier_id == offer.supplier_id,
        StockCatalogOffer.is_current == True
    ).first()
    
    assert new_offer is not None
    assert float(new_offer.price) == new_price
    
    # A antiga deve estar inativa (is_current = False)
    old_offer_check = db.query(StockCatalogOffer).filter(
        StockCatalogOffer.id == offer.id
    ).first()
    assert old_offer_check.is_current is False
    
    # Verificar log de histórico
    history = db.query(StockCatalogPriceHistory).filter(
        StockCatalogPriceHistory.item_id == item.id,
        StockCatalogPriceHistory.supplier_id == offer.supplier_id
    ).first()
    
    assert history is not None
    assert float(history.new_price) == new_price
    assert float(history.old_price) == old_price
    assert history.changed_by_user_id == admin_user.id

    audit = db.query(AuditLog).filter(AuditLog.action == "stock.price_updated").first()
    assert audit is not None
    assert audit.module == "stock"
    assert audit.details["item_id"] == str(item.id)
    assert audit.details["supplier_id"] == str(offer.supplier_id)

    event = db.query(EventLog).filter(EventLog.event_type == "stock.price_updated").first()
    assert event is not None
    assert event.aggregate_id == str(item.id)
    assert event.payload["supplier_id"] == str(offer.supplier_id)


def test_price_update_rejects_invalid_price_and_supplier(db: Session):
    """
    Garante que a atualizacao manual nao altera a variacao quando preco ou fornecedor nao batem.
    """
    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    admin_user = db.query(User).filter(User.role_id == admin_role.id).first()
    item, offer, other_offer = create_minimal_stock_item(db)

    assert item is not None
    assert offer is not None
    assert other_offer is not None

    with pytest.raises(ValueError, match="maior que zero"):
        StockCatalogService.update_item_price(
            db=db,
            item_id=item.id,
            supplier_id=offer.supplier_id,
            new_price=-1,
            user_id=admin_user.id,
        )

    with pytest.raises(ValueError, match="oferta ativa"):
        StockCatalogService.update_item_price(
            db=db,
            item_id=item.id,
            supplier_id=other_offer.supplier_id,
            new_price=99,
            user_id=admin_user.id,
        )

    current_offer = db.query(StockCatalogOffer).filter(StockCatalogOffer.id == offer.id).first()
    assert current_offer.is_current is True

def test_quote_draft_generation(db: Session):
    """
    Valida a geração de payload de cotação sem disparos externos.
    """
    item, _, _ = create_minimal_stock_item(db)
    payload = StockCatalogService.create_quote_draft(db, item.id)
    
    assert payload["product_item_id"] == str(item.id)
    assert payload["display_name"] == item.display_name
    assert "suggested_suppliers" in payload
    # Garantir que não chamou e-mail ou n8n real (é apenas um rascunho de dados)
    assert payload["observations"].startswith("Rascunho gerado a partir do Catálogo.")


def test_unified_master_catalog_operational_search_and_offers(db: Session):
    """
    Valida a Sprint 1 com o arquivo unificado: PostgreSQL como snapshot,
    itens reais consultaveis, sugestoes leves e ofertas sem misturar variacoes.
    """
    require_real_stock_workbook(UNIFIED_PATH, "Planilha unificada do catalogo mestre")

    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    admin_user = db.query(User).filter(User.role_id == admin_role.id).first()

    result = StockCatalogService.import_unified(UNIFIED_PATH, db, user_id=admin_user.id)
    assert result["status"] == "SUCCESS"
    assert result["total_items"] > 0
    assert result["total_offers"] > 0

    tubo_38_results = StockCatalogService.search_catalog(
        db,
        'Tubo Aço Redondo Polido 1020 3/8',
        current_user=None,
        limit=10,
    )
    assert any('3/8"' in item["display_name"] for item in tubo_38_results)
    tubo_38 = next(item for item in tubo_38_results if '3/8"' in item["display_name"])
    assert tubo_38["last_price"] == 30.69
    assert tubo_38["last_supplier"] == "FAM"

    db_item = db.query(StockCatalogItem).filter(StockCatalogItem.id == uuid.UUID(tubo_38["id"])).first()
    offers_38 = StockCatalogService.get_item_offers(db, db_item.id)
    prices_38 = sorted(float(offer["price"]) for offer in offers_38 if offer["price"] is not None)
    assert prices_38 == [30.69]
    assert offers_38[0]["final_value"] == 5.12
    assert offers_38[0]["email"]

    tubo_112_results = StockCatalogService.search_catalog(db, 'Tubo Aço Redondo Polido 1020 1.1/2', limit=10)
    assert any('1.1/2"' in item["display_name"] for item in tubo_112_results)
    tubo_112 = next(item for item in tubo_112_results if '1.1/2"' in item["display_name"])
    assert tubo_112["last_price"] == 70.50
    assert tubo_112["id"] != tubo_38["id"]

    cobre_item = db.query(StockCatalogItem).filter(StockCatalogItem.internal_code == "VM10005G03").first()
    assert cobre_item is not None
    assert 'TUBO COBRE 5/8' in cobre_item.display_name.upper()
    assert cobre_item.active is True
    assert cobre_item.visibility_scope == "COMMON"

    parafuso_allen_results = StockCatalogService.search_catalog(db, 'Parafuso Allen', limit=20)
    assert parafuso_allen_results
    assert any("ALLEN" in item["display_name"].upper() for item in parafuso_allen_results)

    paraf_allen_results = StockCatalogService.search_catalog(db, 'Paraf allen', limit=20)
    assert paraf_allen_results
    assert any("ALLEN" in item["display_name"].upper() for item in paraf_allen_results)

    parafuso_allen_inox_results = StockCatalogService.search_catalog(db, 'Parafuso Allen Inox', limit=20)
    assert parafuso_allen_inox_results
    assert any("INOX" in item["display_name"].upper() for item in parafuso_allen_inox_results)

    alfapar_results = StockCatalogService.search_catalog(db, 'ALFAPAR', limit=20)
    assert alfapar_results
    assert all(item["display_name"].upper() != "ALFAPAR" for item in alfapar_results)

    suggestions = StockCatalogService.list_items(db, q="tubo", suggest=True, current_user=None)
    assert 0 < len(suggestions) <= 6

    tree = StockCatalogService.get_tree(db, current_user=None)
    assert len(tree) > 1
    assert any(category["title"] != "Outros" for category in tree)
    assert any(
        "tubo" in category["title"].lower() or "tubo" in category["breadcrumb"].lower()
        for category in tree
    )
    flat_titles = []
    for category in tree:
        flat_titles.append(category["title"])
        for family in category.get("children", []):
            flat_titles.append(family["title"])
    assert all(not title.startswith("02.9 ") for title in flat_titles)


def test_measure_name_stripping_and_dynamic_deduplication():
    # Test 1: Naming stripping functions correctly for parenthesized dimensions and suffixes
    name1 = 'Cantoneira Ferro - 6 Mt - (38,1 mm x 3,18 mm)'
    name2 = 'Cantoneira Ferro - 6 Mt - 1.1/2" x 1/8"'
    name3 = 'Cantoneira Inox - 6 Mt - 3"'
    
    assert strip_measurements_from_name(name1) == "Cantoneira Ferro - 6 Mt"
    assert strip_measurements_from_name(name2) == "Cantoneira Ferro - 6 Mt"
    assert strip_measurements_from_name(name3) == "Cantoneira Inox - 6 Mt"

    # Test 2: _deduplicate_public_items correctly merges items with identical stripped names and canonical measure keys
    items = [
        {
            "id": "item-uuid-1",
            "base_name": "Cantoneira Ferro - 6 Mt - (38,1 mm x 3,18 mm)",
            "display_name": "Cantoneira Ferro - 6 Mt - (38,1 mm x 3,18 mm)",
            "family_path": "Cantoneira > Cantoneira Ferro - 6 Mt",
            "source_sheet": "Cantoneira",
            "_canonical_measure_key": "mm:38.10x3.18",
            "measure_kind": "complete",
            "cybersul_code": "VM10009F01",
            "primary_supplier": "FAM",
            "primary_price": 368.00,
            "offer_count": 1
        },
        {
            "id": "item-uuid-2",
            "base_name": "Cantoneira Ferro - 6 Mt - 1.1/2\" x 1/8\"",
            "display_name": "Cantoneira Ferro - 6 Mt - 1.1/2\" x 1/8\"",
            "family_path": "Cantoneira > Cantoneira Ferro - 6 Mt",
            "source_sheet": "Cantoneira",
            "_canonical_measure_key": "mm:38.10x3.18",
            "measure_kind": "complete",
            "cybersul_code": None,
            "primary_supplier": "Vinifer",
            "primary_price": 355.00,
            "offer_count": 1
        }
    ]

    deduped = StockCatalogService._deduplicate_public_items(items)
    
    # Assert they are merged into 1 item
    assert len(deduped) == 1
    merged = deduped[0]
    
    # Check that code, price, and offer count are preserved and merged correctly
    assert merged["cybersul_code"] == "VM10009F01"  # code should prevail
    assert merged["offer_count"] == 2               # offer count should sum up
    assert merged["primary_price"] == 368.00        # primary price/supplier is selected from the higher-scored item
