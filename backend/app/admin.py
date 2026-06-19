from sqladmin import ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.models.user import User
from app.models.violation import Violation
from app.models.hotspot import Hotspot
from app.models.station_stats import StationStats
from app.models.pipeline_run import PipelineRun
from app.models.heatmap import HeatmapGrid

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = form.get("username"), form.get("password")
        
        if username == "admin" and password == "parksense2026":
            request.session.update({"token": "admin_logged_in"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        return True

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.email, User.is_active, User.role]
    icon = "fa-solid fa-user"

class ViolationAdmin(ModelView, model=Violation):
    column_list = [Violation.violation_number, Violation.police_station, Violation.violation_date, Violation.violation_type]
    icon = "fa-solid fa-car-burst"

class HotspotAdmin(ModelView, model=Hotspot):
    column_list = [Hotspot.id, Hotspot.cluster_label, Hotspot.police_station, Hotspot.congestion_impact_score, Hotspot.cis_tier]
    icon = "fa-solid fa-fire"

class StationStatsAdmin(ModelView, model=StationStats):
    column_list = [StationStats.id, StationStats.police_station, StationStats.total_violations, StationStats.cis_avg]
    icon = "fa-solid fa-building-shield"

class PipelineRunAdmin(ModelView, model=PipelineRun):
    column_list = [PipelineRun.id, PipelineRun.run_type, PipelineRun.status, PipelineRun.started_at, PipelineRun.records_processed]
    icon = "fa-solid fa-database"

class HeatmapGridAdmin(ModelView, model=HeatmapGrid):
    column_list = [HeatmapGrid.id, HeatmapGrid.cell_lat, HeatmapGrid.cell_lon, HeatmapGrid.density, HeatmapGrid.time_slice]
    icon = "fa-solid fa-map"
