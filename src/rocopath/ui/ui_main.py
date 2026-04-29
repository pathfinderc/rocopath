# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
##
## Created by: Qt User Interface Compiler version 6.11.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QStatusBar, QTabWidget,
    QTextBrowser, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(977, 667)
        self.action_import = QAction(MainWindow)
        self.action_import.setObjectName(u"action_import")
        self.action_export = QAction(MainWindow)
        self.action_export.setObjectName(u"action_export")
        self.action_about = QAction(MainWindow)
        self.action_about.setObjectName(u"action_about")
        self.action_main_map = QAction(MainWindow)
        self.action_main_map.setObjectName(u"action_main_map")
        self.action_magic_map = QAction(MainWindow)
        self.action_magic_map.setObjectName(u"action_magic_map")
        self.action_key = QAction(MainWindow)
        self.action_key.setObjectName(u"action_key")
        self.action_compatible_export = QAction(MainWindow)
        self.action_compatible_export.setObjectName(u"action_compatible_export")
        self.action_import_point = QAction(MainWindow)
        self.action_import_point.setObjectName(u"action_import_point")
        self.action_export_point = QAction(MainWindow)
        self.action_export_point.setObjectName(u"action_export_point")
        self.action_export_route = QAction(MainWindow)
        self.action_export_route.setObjectName(u"action_export_route")
        self.action_new_compatible_export = QAction(MainWindow)
        self.action_new_compatible_export.setObjectName(u"action_new_compatible_export")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout_3 = QHBoxLayout(self.centralwidget)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.search_group = QGroupBox(self.centralwidget)
        self.search_group.setObjectName(u"search_group")
        self.horizontalLayout_2 = QHBoxLayout(self.search_group)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.line_search = QLineEdit(self.search_group)
        self.line_search.setObjectName(u"line_search")

        self.horizontalLayout_2.addWidget(self.line_search)

        self.search_button = QPushButton(self.search_group)
        self.search_button.setObjectName(u"search_button")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.search_button.sizePolicy().hasHeightForWidth())
        self.search_button.setSizePolicy(sizePolicy)

        self.horizontalLayout_2.addWidget(self.search_button)

        self.horizontalLayout_2.setStretch(0, 3)
        self.horizontalLayout_2.setStretch(1, 1)

        self.verticalLayout_2.addWidget(self.search_group)

        self.point_filter = QGroupBox(self.centralwidget)
        self.point_filter.setObjectName(u"point_filter")
        self.horizontalLayout = QHBoxLayout(self.point_filter)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.tabWidget = QTabWidget(self.point_filter)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab_1 = QWidget()
        self.tab_1.setObjectName(u"tab_1")
        self.tabWidget.addTab(self.tab_1, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.tabWidget.addTab(self.tab_2, "")
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        self.tabWidget.addTab(self.tab_3, "")

        self.horizontalLayout.addWidget(self.tabWidget)


        self.verticalLayout_2.addWidget(self.point_filter)

        self.verticalLayout_2.setStretch(0, 1)
        self.verticalLayout_2.setStretch(1, 9)

        self.horizontalLayout_3.addLayout(self.verticalLayout_2)

        self.map_group = QGroupBox(self.centralwidget)
        self.map_group.setObjectName(u"map_group")

        self.horizontalLayout_3.addWidget(self.map_group)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.route_group = QGroupBox(self.centralwidget)
        self.route_group.setObjectName(u"route_group")
        self.verticalLayout_3 = QVBoxLayout(self.route_group)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.select_all = QPushButton(self.route_group)
        self.select_all.setObjectName(u"select_all")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.select_all.sizePolicy().hasHeightForWidth())
        self.select_all.setSizePolicy(sizePolicy1)

        self.horizontalLayout_5.addWidget(self.select_all)

        self.clear_select = QPushButton(self.route_group)
        self.clear_select.setObjectName(u"clear_select")

        self.horizontalLayout_5.addWidget(self.clear_select)

        self.reset_all = QPushButton(self.route_group)
        self.reset_all.setObjectName(u"reset_all")
        sizePolicy1.setHeightForWidth(self.reset_all.sizePolicy().hasHeightForWidth())
        self.reset_all.setSizePolicy(sizePolicy1)

        self.horizontalLayout_5.addWidget(self.reset_all)


        self.verticalLayout_3.addLayout(self.horizontalLayout_5)

        self.select_num = QLabel(self.route_group)
        self.select_num.setObjectName(u"select_num")

        self.verticalLayout_3.addWidget(self.select_num)

        self.start_status = QLabel(self.route_group)
        self.start_status.setObjectName(u"start_status")

        self.verticalLayout_3.addWidget(self.start_status)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.plan_route = QPushButton(self.route_group)
        self.plan_route.setObjectName(u"plan_route")
        sizePolicy1.setHeightForWidth(self.plan_route.sizePolicy().hasHeightForWidth())
        self.plan_route.setSizePolicy(sizePolicy1)
        self.plan_route.setMaximumSize(QSize(80, 16777215))

        self.horizontalLayout_6.addWidget(self.plan_route)

        self.remove_select = QPushButton(self.route_group)
        self.remove_select.setObjectName(u"remove_select")
        self.remove_select.setMaximumSize(QSize(100, 16777215))

        self.horizontalLayout_6.addWidget(self.remove_select)

        self.merge_select = QPushButton(self.route_group)
        self.merge_select.setObjectName(u"merge_select")
        self.merge_select.setMaximumSize(QSize(100, 16777215))

        self.horizontalLayout_6.addWidget(self.merge_select)


        self.verticalLayout_3.addLayout(self.horizontalLayout_6)


        self.verticalLayout.addWidget(self.route_group)

        self.groupBox = QGroupBox(self.centralwidget)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_4 = QVBoxLayout(self.groupBox)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.help_text = QTextBrowser(self.groupBox)
        self.help_text.setObjectName(u"help_text")

        self.verticalLayout_4.addWidget(self.help_text)


        self.verticalLayout.addWidget(self.groupBox)

        self.info_group = QGroupBox(self.centralwidget)
        self.info_group.setObjectName(u"info_group")
        self.horizontalLayout_4 = QHBoxLayout(self.info_group)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.point_info = QTextBrowser(self.info_group)
        self.point_info.setObjectName(u"point_info")

        self.horizontalLayout_4.addWidget(self.point_info)


        self.verticalLayout.addWidget(self.info_group)

        self.verticalLayout.setStretch(0, 3)
        self.verticalLayout.setStretch(1, 3)
        self.verticalLayout.setStretch(2, 4)

        self.horizontalLayout_3.addLayout(self.verticalLayout)

        self.horizontalLayout_3.setStretch(0, 2)
        self.horizontalLayout_3.setStretch(1, 5)
        self.horizontalLayout_3.setStretch(2, 2)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 977, 33))
        self.menu_file = QMenu(self.menubar)
        self.menu_file.setObjectName(u"menu_file")
        self.menu_help = QMenu(self.menubar)
        self.menu_help.setObjectName(u"menu_help")
        self.menu_map = QMenu(self.menubar)
        self.menu_map.setObjectName(u"menu_map")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menu_file.menuAction())
        self.menubar.addAction(self.menu_map.menuAction())
        self.menubar.addAction(self.menu_help.menuAction())
        self.menu_file.addAction(self.action_import)
        self.menu_file.addAction(self.action_export_point)
        self.menu_file.addAction(self.action_export)
        self.menu_file.addAction(self.action_compatible_export)
        self.menu_file.addAction(self.action_new_compatible_export)
        self.menu_file.addAction(self.action_export_route)
        self.menu_file.addSeparator()
        self.menu_help.addAction(self.action_key)
        self.menu_help.addAction(self.action_about)
        self.menu_map.addAction(self.action_main_map)
        self.menu_map.addAction(self.action_magic_map)

        self.retranslateUi(MainWindow)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"\u6d1b\u5bfb", None))
        self.action_import.setText(QCoreApplication.translate("MainWindow", u"\u5bfc\u5165\u70b9\u4f4d", None))
        self.action_export.setText(QCoreApplication.translate("MainWindow", u"\u5bfc\u51fa\u5168\u90e8", None))
        self.action_about.setText(QCoreApplication.translate("MainWindow", u"\u5173\u4e8e", None))
        self.action_main_map.setText(QCoreApplication.translate("MainWindow", u"\u5361\u7f57\u897f\u4e9a", None))
        self.action_magic_map.setText(QCoreApplication.translate("MainWindow", u"\u9b54\u6cd5\u5b66\u9662", None))
        self.action_key.setText(QCoreApplication.translate("MainWindow", u"\u952e\u4f4d", None))
        self.action_compatible_export.setText(QCoreApplication.translate("MainWindow", u"\u5bfc\u51fa\u517c\u5bb9\u683c\u5f0f(6.0\u4e4b\u524d\uff09", None))
        self.action_import_point.setText(QCoreApplication.translate("MainWindow", u"\u5bfc\u5165\u70b9\u4f4d", None))
        self.action_export_point.setText(QCoreApplication.translate("MainWindow", u"\u5bfc\u51fa\u70b9\u4f4d", None))
        self.action_export_route.setText(QCoreApplication.translate("MainWindow", u"\u5bfc\u51fa\u8def\u5f84", None))
        self.action_new_compatible_export.setText(QCoreApplication.translate("MainWindow", u"\u5bfc\u51fa\u517c\u5bb9\u683c\u5f0f\uff086.0\u53ca\u4e4b\u540e\uff09", None))
        self.search_group.setTitle(QCoreApplication.translate("MainWindow", u"\u641c\u7d22", None))
        self.line_search.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u641c\u7d22\u70b9\u4f4d\u540d\u79f0", None))
        self.search_button.setText(QCoreApplication.translate("MainWindow", u"\u67e5\u8be2", None))
        self.point_filter.setTitle(QCoreApplication.translate("MainWindow", u"\u70b9\u4f4d\u7b5b\u9009", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_1), QCoreApplication.translate("MainWindow", u"\u5e38\u7528", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("MainWindow", u"\u81ea\u5b9a\u4e49", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), QCoreApplication.translate("MainWindow", u"\u9ad8\u7ea7", None))
        self.map_group.setTitle(QCoreApplication.translate("MainWindow", u"\u5730\u56fe", None))
        self.route_group.setTitle(QCoreApplication.translate("MainWindow", u"\u8def\u7ebf\u89c4\u5212", None))
        self.select_all.setText(QCoreApplication.translate("MainWindow", u"\u5168\u9009", None))
        self.clear_select.setText(QCoreApplication.translate("MainWindow", u"\u6e05\u7a7a\u9009\u4e2d\u72b6\u6001", None))
        self.reset_all.setText(QCoreApplication.translate("MainWindow", u"\u6e05\u7a7a\u5168\u90e8", None))
        self.select_num.setText(QCoreApplication.translate("MainWindow", u"\u9009\u4e2d\u70b9\u4f4d\uff1a", None))
        self.start_status.setText(QCoreApplication.translate("MainWindow", u"\u8d77\u70b9\uff1a", None))
        self.plan_route.setText(QCoreApplication.translate("MainWindow", u"\u89c4\u5212\u8def\u5f84", None))
        self.remove_select.setText(QCoreApplication.translate("MainWindow", u"\u79fb\u9664\u8fb9", None))
        self.merge_select.setText(QCoreApplication.translate("MainWindow", u"\u5408\u5e76\u9009\u4e2d\u8def\u5f84", None))
        self.groupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u4f7f\u7528\u8bf4\u660e", None))
        self.info_group.setTitle(QCoreApplication.translate("MainWindow", u"\u70b9\u4f4d\u4fe1\u606f", None))
        self.menu_file.setTitle(QCoreApplication.translate("MainWindow", u"\u6587\u4ef6", None))
        self.menu_help.setTitle(QCoreApplication.translate("MainWindow", u"\u5e2e\u52a9", None))
        self.menu_map.setTitle(QCoreApplication.translate("MainWindow", u"\u5730\u56fe", None))
    # retranslateUi

