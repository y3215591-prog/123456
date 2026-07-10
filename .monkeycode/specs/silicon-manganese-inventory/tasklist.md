# 需求实施计划

- [x] 1. 项目结构初始化与核心配置
  - 创建项目目录结构（ui/services/dao/models/utils）
  - 编写 config.py（数据库路径、应用名称等配置项）
  - 编写 main.py 应用入口（QApplication 启动 + MainWindow 初始化）
  - 编写 requirements.txt（PySide6、openpyxl 依赖）
  - 为配置模块编写单元测试

- [ ] 2. 数据库层实现
  - [x] 2.1 实现数据库连接管理器
    - 编写 database.py（SQLite 连接、自动建表、数据库文件初始化）
    - 实现首次启动时自动创建全部 15 张表结构（需求14.1）
    - 实现数据库备份导出和恢复功能（需求14.3、14.4）
    - 为数据库连接和建表编写单元测试

  - [x] 2.2 实现铅封号数据访问层
    - 编写 seal_dao.py（seal_numbers + seal_batches 表 CRUD）
    - 实现按状态批量查询铅封号方法
    - 实现号段导入时的批量插入和重叠校验（需求10.4）
    - 为铅封号 DAO 编写单元测试

  - [x] 2.3 实现入库相关数据访问层
  - [x] 2.4 实现出库数据访问层
  - [x] 2.5 实现化验结果数据访问层
  - [x] 2.6 实现基础数据访问层
- [x] 3. 检查点 - 数据库层全部 DAO 完成，确认表结构可用

- [x] 4. 业务逻辑层实现
  - [x] 4.1 实现铅封号服务
  - [x] 4.2 实现预入库与入库服务
  - [x] 4.3 实现出库服务
  - [x] 4.4 实现化验管理服务
  - [x] 4.5 实现报表与统计服务
  - [x] 4.6 实现 Excel 导入导出服务
- [x] 5. 检查点 - 业务逻辑层全部完成，确认核心流程可执行

- [x] 6. UI 界面层实现
  - [x] 6.1 实现主窗口和导航栏（main_window.py + navbar.py + base_page.py）
  - [x] 6.2 实现预入库页面（pre_inbound_page.py + pre_inbound_dialog.py）
  - [x] 6.3 实现化验结果对话框和入库确认页面（lab_result_dialog.py + inbound_confirm_page.py）
  - [x] 6.4 实现成品库存页面（inventory_page.py）
  - [x] 6.5 实现出库发货页面（outbound_page.py + outbound_dialog.py）
  - [x] 6.6 实现每日发货明细页面（daily_shipment_page.py）
  - [x] 6.7 实现订单装车汇总页面（order_summary_page.py）
  - [x] 6.8 实现 Excel 导入页面（excel_import_page.py）
  - [x] 6.9 实现铅封号管理页面（seal_manage_page.py + seal_import_dialog.py）
  - [x] 6.10 实现库位管理页面（location_page.py）
  - [x] 6.11 实现客户供应商管理页面（customer_page.py）
  - [x] 6.12 实现基础数据管理页面（basic_data_page.py）

- [x] 7. 检查点 - UI 层全部完成，确认所有页面展示正常

- [x] 8. 集成测试与收尾（95 个测试全部通过）
  - [x] 铅封号完整生命周期流程集成测试（号段导入→预入库→化验→入库确认→出库→追溯）
  - [x] Excel 导入全流程测试（销售订单导入自动创建客户/规格、日发货流水导入）
  - [x] 预置常见硅锰合金品名规格数据（FeMn65Si17、SiMn6517、SiMn6014 等）
  - [x] 各报表 Excel 导出功能测试（成品库存、每日发货明细、订单装车汇总）
  - [x] 报表筛选和订单预警功能测试
