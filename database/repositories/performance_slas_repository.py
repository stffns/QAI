"""
Performance SLAs Repository - Enhanced with Hierarchy
====================================================

Repository para SLAs de performance con soporte completo para jerarquía de relevancia.
Incluye métodos optimizados para búsqueda jerárquica y gestión de SLAs.
"""

from datetime import datetime, time
from typing import List, Optional, Dict, Any, Tuple
from sqlmodel import Session, select, func, or_, and_
from database.repositories.base import BaseRepository
from database.models.performance_slas import PerformanceSLAs, RiskLevel, ValidationStatus, SLAScope

class PerformanceSLAsRepository(BaseRepository[PerformanceSLAs]):
    """Repository para gestión de SLAs de performance con jerarquía"""
    
    def __init__(self, session: Session):
        super().__init__(session, PerformanceSLAs)
    
    # === Búsqueda Jerárquica (Funcionalidad Core) ===
    
    def find_applicable_sla(
        self, 
        app_name: str, 
        environment: str, 
        country_code: Optional[str] = None,
        endpoint_pattern: Optional[str] = None
    ) -> Optional[PerformanceSLAs]:
        """
        Encuentra el SLA más específico aplicable al contexto dado.
        
        Sigue la jerarquía de relevancia:
        1. Endpoint + Country + Environment + App
        2. Country + Environment + App  
        3. Environment + App
        4. App General
        
        Args:
            app_name: Nombre de la aplicación
            environment: Ambiente
            country_code: Código de país (opcional)
            endpoint_pattern: Patrón de endpoint (opcional)
            
        Returns:
            SLA más específico aplicable o None si no hay ninguno
        """
        # Construir condiciones base
        base_conditions = [
            PerformanceSLAs.app_name == app_name,
            PerformanceSLAs.is_active == True
        ]
        
        # Casos específicos por jerarquía (orden de mayor a menor especificidad)
        
        # Nivel 1: Endpoint + Country + Environment + App
        if endpoint_pattern and country_code:
            conditions = base_conditions + [
                PerformanceSLAs.environment == environment,
                PerformanceSLAs.country_code == country_code.upper(),
                PerformanceSLAs.endpoint_pattern == endpoint_pattern,
                PerformanceSLAs.specificity_level == 1
            ]
            
            sla = self.session.exec(
                select(PerformanceSLAs)
                .where(and_(*conditions))
                .order_by(PerformanceSLAs.hierarchy_priority)
            ).first()
            
            if sla:
                return sla
        
        # Nivel 2: Country + Environment + App
        if country_code:
            conditions = base_conditions + [
                PerformanceSLAs.environment == environment,
                PerformanceSLAs.country_code == country_code.upper(),
                or_(
                    PerformanceSLAs.endpoint_pattern.is_(None),
                    PerformanceSLAs.endpoint_pattern == '*'
                ),
                PerformanceSLAs.specificity_level == 2
            ]
            
            sla = self.session.exec(
                select(PerformanceSLAs)
                .where(and_(*conditions))
                .order_by(PerformanceSLAs.hierarchy_priority)
            ).first()
            
            if sla:
                return sla
        
        # Nivel 3: Environment + App
        conditions = base_conditions + [
            PerformanceSLAs.environment == environment,
            or_(
                PerformanceSLAs.country_code.is_(None),
                PerformanceSLAs.country_code == '*'
            ),
            or_(
                PerformanceSLAs.endpoint_pattern.is_(None),
                PerformanceSLAs.endpoint_pattern == '*'
            ),
            PerformanceSLAs.specificity_level == 3
        ]
        
        sla = self.session.exec(
            select(PerformanceSLAs)
            .where(and_(*conditions))
            .order_by(PerformanceSLAs.hierarchy_priority)
        ).first()
        
        if sla:
            return sla
        
        # Nivel 4: App General
        conditions = base_conditions + [
            or_(
                PerformanceSLAs.environment == '*',
                PerformanceSLAs.environment == environment
            ),
            or_(
                PerformanceSLAs.country_code.is_(None),
                PerformanceSLAs.country_code == '*'
            ),
            or_(
                PerformanceSLAs.endpoint_pattern.is_(None),
                PerformanceSLAs.endpoint_pattern == '*'
            ),
            PerformanceSLAs.specificity_level == 4
        ]
        
        return self.session.exec(
            select(PerformanceSLAs)
            .where(and_(*conditions))
            .order_by(PerformanceSLAs.hierarchy_priority)
        ).first()
    
    def get_sla_cascade(
        self,
        app_name: str,
        environment: str,
        country_code: Optional[str] = None,
        endpoint_pattern: Optional[str] = None
    ) -> List[PerformanceSLAs]:
        """
        Obtiene todos los SLAs aplicables en orden de especificidad (cascada).
        
        Returns:
            Lista de SLAs ordenados por prioridad jerárquica
        """
        conditions = [
            PerformanceSLAs.app_name == app_name,
            PerformanceSLAs.is_active == True,
            PerformanceSLAs.allows_cascade == True
        ]
        
        # Construir condiciones complejas para incluir SLAs aplicables
        environment_condition = or_(
            PerformanceSLAs.environment == environment,
            PerformanceSLAs.environment == '*'
        )
        
        country_condition = or_(
            PerformanceSLAs.country_code.is_(None),
            PerformanceSLAs.country_code == '*',
            PerformanceSLAs.country_code == (country_code.upper() if country_code else None)
        )
        
        endpoint_condition = or_(
            PerformanceSLAs.endpoint_pattern.is_(None),
            PerformanceSLAs.endpoint_pattern == '*',
            PerformanceSLAs.endpoint_pattern == endpoint_pattern
        )
        
        conditions.extend([environment_condition, country_condition, endpoint_condition])
        
        return self.session.exec(
            select(PerformanceSLAs)
            .where(and_(*conditions))
            .order_by(PerformanceSLAs.hierarchy_priority, PerformanceSLAs.id)
        ).all()
    
    # === Gestión por Scope ===
    
    def get_by_scope(self, scope: SLAScope, active_only: bool = True) -> List[PerformanceSLAs]:
        """Obtiene SLAs por scope específico"""
        conditions = [PerformanceSLAs.sla_scope == scope]
        if active_only:
            conditions.append(PerformanceSLAs.is_active == True)
        
        return self.session.exec(
            select(PerformanceSLAs)
            .where(and_(*conditions))
            .order_by(PerformanceSLAs.hierarchy_priority)
        ).all()
    
    def get_endpoint_specific_slas(self, active_only: bool = True) -> List[PerformanceSLAs]:
        """Obtiene SLAs específicos para endpoints (máxima prioridad)"""
        return self.get_by_scope(SLAScope.ENDPOINT_COUNTRY_ENV_APP, active_only)
    
    def get_country_specific_slas(self, active_only: bool = True) -> List[PerformanceSLAs]:
        """Obtiene SLAs específicos por país"""
        return self.get_by_scope(SLAScope.COUNTRY_ENV_APP, active_only)
    
    def get_environment_slas(self, active_only: bool = True) -> List[PerformanceSLAs]:
        """Obtiene SLAs por ambiente"""
        return self.get_by_scope(SLAScope.ENV_APP, active_only)
    
    def get_general_slas(self, active_only: bool = True) -> List[PerformanceSLAs]:
        """Obtiene SLAs generales de aplicación"""
        return self.get_by_scope(SLAScope.APP_GENERAL, active_only)
    
    # === Filtros Específicos ===
    
    def get_by_app_environment(self, app_name: str, environment: str) -> List[PerformanceSLAs]:
        """Obtiene todos los SLAs para una app y ambiente específicos"""
        return self.session.exec(
            select(PerformanceSLAs)
            .where(
                PerformanceSLAs.app_name == app_name,
                PerformanceSLAs.environment == environment,
                PerformanceSLAs.is_active == True
            )
            .order_by(PerformanceSLAs.hierarchy_priority)
        ).all()
    
    def get_by_country(self, country_code: str, active_only: bool = True) -> List[PerformanceSLAs]:
        """Obtiene SLAs por código de país"""
        conditions = [PerformanceSLAs.country_code == country_code.upper()]
        if active_only:
            conditions.append(PerformanceSLAs.is_active == True)
        
        return self.session.exec(
            select(PerformanceSLAs)
            .where(and_(*conditions))
            .order_by(PerformanceSLAs.hierarchy_priority)
        ).all()
    
    def get_by_risk_level(self, risk_level: RiskLevel, active_only: bool = True) -> List[PerformanceSLAs]:
        """Obtiene SLAs por nivel de riesgo"""
        conditions = [PerformanceSLAs.risk_level == risk_level]
        if active_only:
            conditions.append(PerformanceSLAs.is_active == True)
        
        return self.session.exec(
            select(PerformanceSLAs)
            .where(and_(*conditions))
            .order_by(PerformanceSLAs.hierarchy_priority)
        ).all()
    
    def get_requiring_approval(self, active_only: bool = True) -> List[PerformanceSLAs]:
        """Obtiene SLAs que requieren aprobación manual"""
        conditions = [PerformanceSLAs.requires_approval == True]
        if active_only:
            conditions.append(PerformanceSLAs.is_active == True)
        
        return self.session.exec(
            select(PerformanceSLAs)
            .where(and_(*conditions))
            .order_by(PerformanceSLAs.hierarchy_priority)
        ).all()
    
    # === Estadísticas y Análisis ===
    
    def get_hierarchy_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la jerarquía de SLAs"""
        stats = {}
        
        # Distribución por scope
        scope_stats = self.session.exec(
            select(
                PerformanceSLAs.sla_scope,
                func.count(PerformanceSLAs.id).label('count'),
                func.avg(PerformanceSLAs.hierarchy_priority).label('avg_priority')
            )
            .where(PerformanceSLAs.is_active == True)
            .group_by(PerformanceSLAs.sla_scope)
        ).all()
        
        stats['scope_distribution'] = {
            row.sla_scope: {
                'count': row.count,
                'avg_priority': round(row.avg_priority, 2)
            }
            for row in scope_stats
        }
        
        # Distribución por nivel de riesgo
        risk_stats = self.session.exec(
            select(
                PerformanceSLAs.risk_level,
                func.count(PerformanceSLAs.id).label('count')
            )
            .where(PerformanceSLAs.is_active == True)
            .group_by(PerformanceSLAs.risk_level)
        ).all()
        
        stats['risk_distribution'] = {
            row.risk_level: row.count
            for row in risk_stats
        }
        
        # SLAs por aplicación
        app_stats = self.session.exec(
            select(
                PerformanceSLAs.app_name,
                func.count(PerformanceSLAs.id).label('sla_count'),
                func.min(PerformanceSLAs.hierarchy_priority).label('highest_priority')
            )
            .where(PerformanceSLAs.is_active == True)
            .group_by(PerformanceSLAs.app_name)
            .order_by(func.count(PerformanceSLAs.id).desc())
        ).all()
        
        stats['app_coverage'] = {
            row.app_name: {
                'sla_count': row.sla_count,
                'highest_priority': row.highest_priority
            }
            for row in app_stats
        }
        
        # Total de SLAs activos
        total_active = self.session.exec(
            select(func.count(PerformanceSLAs.id))
            .where(PerformanceSLAs.is_active == True)
        ).one()
        
        stats['total_active_slas'] = total_active
        
        return stats
    
    def get_coverage_gaps(self) -> List[Dict[str, Any]]:
        """Identifica gaps en la cobertura de SLAs"""
        gaps = []
        
        # Apps sin SLAs generales (nivel 4)
        apps_without_general = self.session.exec(
            select(PerformanceSLAs.app_name)
            .where(PerformanceSLAs.is_active == True)
            .group_by(PerformanceSLAs.app_name)
            .having(
                func.sum(
                    func.case((PerformanceSLAs.specificity_level == 4, 1), else_=0)
                ) == 0
            )
        ).all()
        
        for app in apps_without_general:
            gaps.append({
                'type': 'missing_general_sla',
                'app_name': app,
                'description': f"App {app} no tiene SLA general (nivel 4)"
            })
        
        # Ambientes sin cobertura específica
        env_coverage = self.session.exec(
            select(
                PerformanceSLAs.app_name,
                PerformanceSLAs.environment,
                func.count(PerformanceSLAs.id).label('sla_count')
            )
            .where(PerformanceSLAs.is_active == True)
            .group_by(PerformanceSLAs.app_name, PerformanceSLAs.environment)
            .having(func.count(PerformanceSLAs.id) == 1)
        ).all()
        
        for coverage in env_coverage:
            gaps.append({
                'type': 'single_sla_environment',
                'app_name': coverage.app_name,
                'environment': coverage.environment,
                'description': f"Ambiente {coverage.environment} de {coverage.app_name} solo tiene 1 SLA"
            })
        
        return gaps
    
    # === Validación y Mantenimiento ===
    
    def get_pending_validation(self) -> List[PerformanceSLAs]:
        """Obtiene SLAs pendientes de validación"""
        return self.session.exec(
            select(PerformanceSLAs)
            .where(
                PerformanceSLAs.validation_status == ValidationStatus.PENDING,
                PerformanceSLAs.is_active == True
            )
            .order_by(PerformanceSLAs.created_at.desc())
        ).all()
    
    def get_expired_slas(self, days_threshold: int = 90) -> List[PerformanceSLAs]:
        """Obtiene SLAs que no han sido validados en X días"""
        threshold_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - \
                        datetime.timedelta(days=days_threshold)
        
        return self.session.exec(
            select(PerformanceSLAs)
            .where(
                or_(
                    PerformanceSLAs.last_validated_at.is_(None),
                    PerformanceSLAs.last_validated_at < threshold_date
                ),
                PerformanceSLAs.is_active == True
            )
            .order_by(PerformanceSLAs.last_validated_at.asc())
        ).all()
    
    def validate_sla(self, sla_id: int, status: ValidationStatus) -> bool:
        """Marca un SLA como validado"""
        sla = self.get_by_id(sla_id)
        if not sla:
            return False
        
        sla.validation_status = status
        sla.last_validated_at = datetime.utcnow()
        sla.updated_at = datetime.utcnow()
        
        self.session.add(sla)
        self.session.commit()
        return True
    
    def recalculate_hierarchy(self, sla_id: int) -> bool:
        """Recalcula los valores de jerarquía para un SLA"""
        sla = self.get_by_id(sla_id)
        if not sla:
            return False
        
        sla.calculate_hierarchy_values()
        sla.updated_at = datetime.utcnow()
        
        self.session.add(sla)
        self.session.commit()
        return True
    
    def bulk_recalculate_hierarchy(self) -> int:
        """Recalcula jerarquía para todos los SLAs activos"""
        slas = self.session.exec(
            select(PerformanceSLAs)
            .where(PerformanceSLAs.is_active == True)
        ).all()
        
        count = 0
        for sla in slas:
            sla.calculate_hierarchy_values()
            sla.updated_at = datetime.utcnow()
            self.session.add(sla)
            count += 1
        
        self.session.commit()
        return count
    
    # === Métodos de Creación Optimizados ===
    
    def create_with_hierarchy(self, sla_data: Dict[str, Any]) -> PerformanceSLAs:
        """Crea un SLA calculando automáticamente la jerarquía"""
        sla = PerformanceSLAs(**sla_data)
        sla.calculate_hierarchy_values()
        
        return self.create(sla)
    
    def bulk_create_with_hierarchy(self, slas_data: List[Dict[str, Any]]) -> List[PerformanceSLAs]:
        """Crea múltiples SLAs calculando jerarquía automáticamente"""
        slas = []
        
        for sla_data in slas_data:
            sla = PerformanceSLAs(**sla_data)
            sla.calculate_hierarchy_values()
            slas.append(sla)
        
        self.session.add_all(slas)
        self.session.commit()
        
        for sla in slas:
            self.session.refresh(sla)
        
        return slas
