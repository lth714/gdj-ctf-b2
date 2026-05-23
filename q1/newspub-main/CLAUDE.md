# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NewsPub (UJCMS) is a Java-based news content management system using SpringBoot, MyBatis, Spring Security, FreeMarker templating, and Vue3 admin UI. Supports both traditional template rendering and headless CMS (API-first) modes.

## Build & Run Commands

```bash
# Build JAR package
mvn package -P jar

# Build WAR package (for Tomcat deployment)
mvn package -P war

# Run locally (JAR mode auto-deploys static resources)
java -jar target/news-*.jar

# Run with Maven
mvn spring-boot:run

# Auto-generate MyBatis mappers (requires config in pom.xml)
mvn mybatis-generator:generate
```

## Technology Stack

- **Framework:** Spring Boot 2.7.18 / Spring Framework 5.3.39
- **ORM:** MyBatis 2.3.2 + PageHelper
- **Database:** MySQL 8.0 (supports PostgreSQL, Oracle, 国产数据库)
- **Migration:** Liquibase 4.5.0 (auto-creates tables on first run)
- **Templating:** FreeMarker (frontend templates in `src/main/webapp/templates`)
- **Search:** Lucene 8.11.1 with jcseg/IK Chinese tokenizers
- **Workflow:** Flowable 6.8.1
- **Auth:** Spring Security + JWT
- **Cache:** Caffeine (default) / Redis

## High-Level Architecture

### Package Structure
```
com.ujcms.cms/
├── Application.java              # Main entry point
├── core/
│   ├── domain/
│   │   ├── base/                 # Entity base classes (XxxBase)
│   │   ├── cache/                # Cache implementations
│   │   └── *.java                # Domain entities
│   ├── mapper/                   # MyBatis mapper interfaces
│   ├── service/                  # Service layer
│   │   ├── args/                 # Query builder classes (XxxArgs)
│   │   └── *.java                # Service implementations
│   └── web/
│       ├── api/                  # Public REST API controllers
│       ├── backendapi/           # Admin REST API controllers
│       ├── frontend/             # Page controllers (freemarker templates)
│       ├── directive/            # FreeMarker custom directives
│       └── support/              # Interceptors, exception handlers, resolvers
└── util/                         # Utility classes
```

### Controller Pattern
- **`/api/`** — Public REST API (CORS open, no auth required for some endpoints)
- **`/backendapi/`** — Admin REST API (requires authentication)
- **`/cp/`** — Admin frontend (Vue-based, served from `src/main/webapp/cp/`)
- **`/`** — Frontend pages (FreeMarker templates)

### Entity Pattern
Entities use a **base class pattern**:
- `XxxBase.java` — Contains all fields with getters/setters
- `Xxx.java` — Extends `XxxBase`, adds business methods

Example: `Article` extends `ArticleBase`, which contains all article fields.

### Service Pattern
Services follow a query-builder pattern:
- `XxxService.java` — Business logic
- `args/XxxArgs.java` — Query conditions (uses MyBatis `Wrapper`-style pattern)

### Database Auto-Initialization
- Liquibase creates tables automatically on first run
- Changelog files: `src/main/resources/db/changelog/`
- Initial data: `src/main/resources/db/data.mysql.sql`
- To disable: set `spring.liquibase.enabled: false` and `news.data-sql-enabled: false`

## Configuration

Main config: `src/main/resources/application.yaml`

Key settings:
- `spring.datasource.url` — JDBC connection URL
- `spring.datasource.username/password` — Database credentials
- `server.port` — Default: 80
- `spring.freemarker.template-loader-path` — Template directory
- `ujcms.lucene-path` — Lucene index storage (default: `/WEB-INF/lucene`)
- `ujcms.uploads-location` — Upload file storage (default: `/uploads`)

## Security Notes

- FreeMarker `new_builtin_class_resolver: allows_nothing` — prevents RCE via template
- Default admin: `admin` / `password`
- JWT session timeout: 30 minutes (`jwt.sessionTimeout`)
- Password pepper configured for additional hash security

## Database Connection

Supports multiple databases via JDBC. Default MySQL:
```
spring.datasource.url: jdbc:mysql://localhost:3306/news?serverTimezone=Asia/Shanghai&characterEncoding=UTF-8
spring.datasource.username: root
spring.datasource.password: Root@2024
```

## Default Access Points

- Frontend: http://localhost/
- Admin UI: http://localhost/cp/ (Vue frontend)
- API Docs: http://localhost/swagger-ui/index.html
