# Vanna MCP Server - Project Planning Document

## 🎯 Project Overview

### Vision
Build a Model Context Protocol (MCP) server that leverages Vanna AI to provide natural language to SQL capabilities for BigQuery data analysis, with self-learning capabilities to improve over time.

### Goals
- Enable natural language querying of BigQuery datasets
- Create a self-learning SQL assistant that improves with usage
- Replace the existing AI Data Analyst MCP if successful
- Provide export capabilities for query results

---

## 📋 Project Specifications

### 1. **Core Functionality**
- **Primary Use Case**: Dual purpose
  - Team queries using natural language
  - Self-learning SQL assistant
- **Query Scope**: SELECT queries only (read-only access)

### 2. **Data Sources & Training**
- **BigQuery Datasets**: All 8 datasets initially (optimize and restrict later)
- **Training Data Sources**:
  - DDL from BigQuery (enhanced with metadata)
  - Data catalog from `metadata_data_dictionary`
  - Historical successful queries
  - Business documentation
- **Integration Approach**: Map all data to Vanna's default format (DDL, documentation, queries)

### 3. **MCP Tools Implementation**

#### Priority Order:
1. **`vanna_ask`** - Convert natural language to SQL
2. **`vanna_train`** - Add training data (DDL, documentation, queries)
3. **`vanna_suggest_questions`** - Show what questions users can ask
4. **`vanna_explain`** - Explain SQL in plain English
5. **`vanna_execute`** - Execute generated SQL queries
6. **`vanna_get_schemas`** - Display database structure
7. **`vanna_get_training_data`** - View existing training data
8. **`vanna_remove_training`** - Remove incorrect training data
9. **`vanna_generate_followup`** - Generate follow-up questions

### 4. **User Experience**
- **Default Response**: Return all information (SQL + explanation + confidence score)
- **Flexibility**: Adjust response based on context/user needs
- **Export Feature**: CSV/Excel export for query results

### 5. **Integration Architecture**
- **BigQuery MCP Tool**: Keep separate
- **AI Data Analyst MCP**: Keep separate (potential replacement)
- **Data Catalog Integration**: 
  - Read from `metadata_data_dictionary` 
  - Enhance DDL with metadata as SQL comments
  - Example:
    ```sql
    CREATE TABLE salesorderheader (
        orderid STRING COMMENT 'Unique order identifier',
        totalvalue NUMERIC COMMENT 'Total order amount - Sample: 1000.50, 2500.00'
    ) COMMENT 'Sales transactions table with 50000 rows';
    ```

### 6. **Learning & Improvement**
- **Approach**: Semi-automated with quality control
- **Successful Queries**: 
  - Log but don't auto-train
  - Weekly review for manual training
- **Failed Queries**: 
  - Log with error details
  - Identify missing patterns
- **User Corrections**: 
  - Immediate training option
  - Mark as high-quality training data
- **Query Validation** (Mandatory for all training):
  - Syntax validation
  - SELECT-only verification
  - Dry run execution (LIMIT 1)
  - Result verification (non-empty)
  - Store execution metadata

### 7. **Security & Access Control**
- **Multi-Tenant Security**: Strict tenant isolation with comprehensive validation
- **Cross-Tenant Protection**: Pre-execution validation to prevent data leakage
- **Database Type Validation**: Type-specific security and feature restrictions
- **Tool Security Standards**: Mandatory security requirements for all tools
- **Access Control**: Whitelist/blacklist configuration
  ```yaml
  access_control:
    mode: "whitelist"  # or "blacklist"
    datasets:
      whitelist: ["ZADLEY_Hevo", "CompanyInt_Hevo", ...]
      # OR
      blacklist: ["sensitive_data", ...]
  ```
- **Query Safety**: Comprehensive SQL validation and filtering
- **Security Documentation**: [Tool Development Standards](docs/TOOL_DEVELOPMENT_STANDARDS.md)

### 8. **Performance & Scalability**
- **Design Principle**: Build for unknown scale, monitor and adjust
- **Architecture**: Scalable design that can grow with usage

### 9. **Success Criteria**
- High SQL generation accuracy
- Faster query writing for team
- Better data understanding through suggestions
- Successful replacement of AI Data Analyst MCP

---

## 💾 Database Schema

### Supabase Schema: `vannabq`
```sql
-- Schema configuration (not hardcoded, from config)
CREATE SCHEMA IF NOT EXISTS vannabq;

-- Core Vanna tables
CREATE TABLE vannabq.training_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    training_data_type VARCHAR(50) NOT NULL, -- 'ddl', 'documentation', 'sql'
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE vannabq.query_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    generated_sql TEXT NOT NULL,
    executed BOOLEAN DEFAULT false,
    execution_time_ms INTEGER,
    row_count INTEGER,
    user_feedback VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE vannabq.access_control (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    control_type VARCHAR(20) NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 🏗️ Technical Architecture

### Technology Stack
- **Language**: Python 3.10+
- **Core Library**: Vanna AI
- **MCP Framework**: FastMCP
- **Vector Database**: Supabase (pgvector) - Schema: `vannabq`
- **LLM**: OpenAI GPT-4 (SQL generation)
- **Embeddings**: OpenAI text-embedding-3-small (similarity search)
- **Data Warehouse**: Google BigQuery
- **Visualization**: Plotly (optional charts)

### Component Design
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Claude Desktop │────▶│  Vanna MCP Server│────▶│     Vanna AI    │
│   (MCP Client)  │     │    (FastMCP)     │     │      Core       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │                          │
                                │                          ▼
                                │                 ┌─────────────────┐
                                │                 │    Supabase     │
                                │                 │   (pgvector)    │
                                │                 └─────────────────┘
                                ▼
                        ┌─────────────────┐
                        │    BigQuery     │
                        │  (8 Datasets)   │
                        └─────────────────┘
```

### Data Flow
1. User asks natural language question via MCP tool
2. Vanna processes with context from Supabase embeddings
3. OpenAI generates SQL
4. Optional execution on BigQuery
5. Results returned with explanation and confidence

---

## 📅 Implementation Phases

### Phase 1: Core Foundation (Week 1-2)
- [ ] Project setup and environment configuration
- [ ] Vanna AI integration with Supabase and OpenAI
- [ ] Implement `vanna_ask` tool
- [ ] Implement `vanna_train` tool
- [ ] Basic testing with sample data

### Phase 2: Training & Data Integration (Week 3-4)
- [ ] Extract DDL from all BigQuery datasets
- [ ] Integrate metadata from `metadata_data_dictionary`
- [ ] Create enhanced DDL with comments
- [ ] Load initial training data
- [ ] Implement `vanna_suggest_questions`

### Phase 3: Extended Features (Week 5-6)
- [ ] Implement `vanna_explain` tool
- [ ] Implement `vanna_execute` tool with:
  - [ ] Data-only response option
  - [ ] Auto-visualization with Plotly
  - [ ] Multiple chart format support (JSON/PNG/SVG)
- [ ] Add CSV/Excel export functionality
- [ ] Implement query validation pipeline
- [ ] Add access control configuration

### Phase 4: Management Tools (Week 7)
⚠️ **CRITICAL: All Phase 4 tools MUST follow [Tool Development Standards](docs/TOOL_DEVELOPMENT_STANDARDS.md)**
- [ ] Implement `vanna_get_schemas` (with security standards compliance)
- [ ] Implement `vanna_get_training_data` (with security standards compliance)
- [ ] Implement `vanna_remove_training` (with security standards compliance)
- [ ] Create training data management workflow
- [ ] Security audit for all Phase 4 tools

### Phase 5: Advanced Features & Polish (Week 8)
⚠️ **CRITICAL: All Phase 5 tools MUST follow [Tool Development Standards](docs/TOOL_DEVELOPMENT_STANDARDS.md)**
- [ ] Implement `vanna_generate_followup` (with security standards compliance)
- [ ] Performance optimization
- [ ] Comprehensive testing (including security compliance testing)
- [ ] Documentation
- [ ] Security audit for all tools
- [ ] Deployment preparation

---

## 🚀 Getting Started (Phase 1 Tasks)

### Initial Setup
1. Create Python virtual environment
2. Install dependencies (vanna, fastmcp, etc.)
3. Configure connections:
   - Supabase (pgvector)
   - OpenAI API
   - BigQuery credentials

### First Implementation
1. Basic MCP server structure
2. Vanna initialization with Supabase
3. Simple `vanna_ask` implementation
4. Testing framework

---

## 📝 Future Enhancements (Wishlist)

- Query history tracking
- Favorite queries functionality
- Query templates
- Advanced analytics on query patterns
- Multi-user support with personalization
- Query cost estimation
- Performance optimization recommendations
- Integration with other data sources

---

## ✅ Definition of Done

The project will be considered successful when:
1. All 9 MCP tools are implemented and working
2. SQL generation accuracy is consistently high
3. The system successfully learns from usage
4. Team finds it faster than writing SQL manually
5. It can effectively replace the AI Data Analyst MCP

---

## 📚 References

- [Vanna.AI Documentation](https://vanna.ai/docs/)
- [FastMCP Documentation](https://github.com/fastmcp/fastmcp)
- [BigQuery Best Practices](https://cloud.google.com/bigquery/docs/best-practices)
- [MCP Specification](https://modelcontextprotocol.io/)

---

*Document Version: 1.0*  
*Created: January 2025*  
*Status: Planning Phase*