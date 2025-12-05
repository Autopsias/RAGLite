# Technical Research: AWS Database Cloud Deployment Options

**Research Date:** 2025-12-05
**Research Type:** Technical Research
**Researcher:** Mary (Business Analyst Agent)
**Research Goals:** Identify cost-effective AWS deployment options for RAGLite databases

---

## Executive Summary

This research evaluates AWS deployment options for RAGLite's databases with the goal of minimizing costs for a very low-traffic workload (~100 queries/week). The analysis covers vector database (Qdrant) and SQL database (PostgreSQL) options across managed services, self-hosted solutions, and bundled deployments.

**Key Finding:** The optimal deployment strategy depends on your priorities:

| Priority | Recommended Approach | Monthly Cost |
|----------|---------------------|--------------|
| **Lowest Cost** | Qdrant Cloud Free + EC2 Spot PostgreSQL | **~$3-4/month** |
| **Simplest Deployment** | Single Lightsail instance (both DBs) | **~$5-7/month** |
| **AWS-Native Managed** | Qdrant Cloud Free + RDS Free Tier | **$0/month** (first 12 months) |
| **Current Story 5.1 Approach** | EC2 t4g.small Spot (both DBs) | **~$5-10/month** |

---

## Current Database Sizing

| Database | Local Size | Details |
|----------|-----------|---------|
| **Qdrant** | 129 MB | 1 collection (`financial_docs`), ~7,200 vectors |
| **PostgreSQL** | 797 MB | `financial_tables`: 769MB (1M rows), `financial_chunks`: 20MB (7.2K rows) |

**Usage Profile:** ~100 queries/week (0.0006 queries/second - extremely low traffic)

---

## Vector Database Options

### Option 1: Qdrant Cloud Free Tier (RECOMMENDED)

**Cost: $0/month (forever)**

| Specification | Value |
|---------------|-------|
| Storage | 1 GB (your data: 129 MB - fits easily) |
| Vectors | ~1 million at 768 dimensions |
| Credit Card | Not required |
| Availability | Single-node (no HA) |
| Regions | AWS, GCP, Azure regions available |

**Pros:**
- Zero cost forever
- Fully managed (no ops overhead)
- 1 GB storage >> your 129 MB requirement
- Built-in monitoring and Web UI
- Automatic updates and security patches

**Cons:**
- No SLA guarantee on free tier
- Single-node only (no HA)
- Rate limits not documented (but sufficient for 100 queries/week)
- Data is outside your AWS VPC

**Production Suitability:** [Medium Confidence] Suitable for your low-traffic workload. Qdrant markets free tier for "development and small projects" but 100 queries/week is well within acceptable limits.

**Sources:**
- [Qdrant Pricing](https://qdrant.tech/pricing/)
- [Qdrant Cloud UI Changes Blog](https://qdrant.tech/blog/product-ui-changes/)

---

### Option 2: Self-Hosted Qdrant on EC2 Spot

**Cost: ~$2-4/month**

| Instance | Specs | Spot Price (us-east-1) | Monthly Cost |
|----------|-------|------------------------|--------------|
| t4g.nano | 0.5 GB RAM, 2 vCPU | ~$0.0016/hr | ~$1.15/month |
| t4g.micro | 1 GB RAM, 2 vCPU | ~$0.003/hr | ~$2.20/month |
| **+ EBS gp3** | 10 GB | $0.08/GB-month | ~$0.80/month |

**Qdrant Memory Requirements (from official benchmarks):**
- All in RAM: ~1.2 GB for 1M vectors (100 dimensions)
- With MMAP (vectors on disk): ~600 MB minimum
- With MMAP (vectors + HNSW on disk): **~135 MB minimum**

**For your 7,200 vectors:** Even t4g.nano (512 MB) with MMAP enabled is sufficient!

**Pros:**
- Very low cost (~$2-3/month)
- Data stays in your AWS VPC
- Full control over configuration
- ARM Graviton2 = 20% cheaper than x86

**Cons:**
- Spot interruptions possible (acceptable per Ricardo)
- Manual ops: patching, backups, monitoring
- No automatic failover

**Sources:**
- [Qdrant Memory Consumption Article](https://qdrant.tech/articles/memory-consumption/)
- [AWS EC2 Spot Pricing](https://aws.amazon.com/ec2/spot/pricing/)

---

### Option 3: Amazon OpenSearch Serverless (NOT RECOMMENDED)

**Cost: ~$174-350/month minimum**

Even with the new half-OCU (0.5 vCPU) minimum introduced in 2024, OpenSearch Serverless has significant base costs:
- Non-redundant: ~$174/month (1 indexing + 1 search half-OCU)
- Redundant: ~$350/month

**Verdict:** Overkill and expensive for 129 MB and 100 queries/week. Not recommended.

---

### Vector DB Recommendation

**Primary: Qdrant Cloud Free Tier ($0/month)**
- Your 129 MB << 1 GB limit
- Zero ops overhead
- Accept minor limitation of data outside VPC

**Fallback: Self-hosted on EC2 Spot t4g.micro (~$3/month)**
- If you require data in VPC
- Enable MMAP for minimal RAM usage

---

## SQL Database Options

### Option 1: AWS RDS Free Tier (RECOMMENDED for first 12 months)

**Cost: $0/month (first 12 months)**

| Specification | Value |
|---------------|-------|
| Instance | db.t3.micro or db.t4g.micro |
| Storage | 20 GB gp2 included |
| Hours | 750 hours/month (enough for 24/7) |
| Backup | Up to 20 GB included |

**Important Note (Dec 2025):** AWS changed free tier structure on July 15, 2025:
- Accounts created **before** July 15, 2025: Classic 12-month free tier
- Accounts created **after** July 15, 2025: Credit-based model (~$100 credits)

**After Free Tier Expires:** ~$12-20/month for smallest instance

**Pros:**
- Fully managed (backups, patching, monitoring)
- Zero cost for first year
- Your 800 MB << 20 GB limit

**Cons:**
- Cost jumps after 12 months
- May be overkill for 100 queries/week

**Sources:**
- [AWS RDS Free Tier](https://aws.amazon.com/rds/free/)
- [AWS Free Tier Changes July 2025](https://dev.to/cloud_man/new-aws-free-tier-updates-after-july-15-2025-what-you-need-to-know-3m36)

---

### Option 2: Amazon Lightsail Managed PostgreSQL

**Cost: $15/month**

| Specification | Value |
|---------------|-------|
| Instance | 1 GB RAM, 1 vCPU |
| Storage | 40 GB SSD included |
| High Availability | $30/month (optional) |

**Pros:**
- Fully managed
- Simple, predictable pricing
- Includes storage and backups

**Cons:**
- $15/month is expensive for 100 queries/week
- Less flexible than RDS

**Verdict:** Not recommended - too expensive for your workload.

---

### Option 3: Aurora Serverless v2 (NOT RECOMMENDED)

**Cost: ~$43-45/month minimum**

| Component | Cost |
|-----------|------|
| Compute | 0.5 ACU minimum × $0.12/ACU-hr × 730 hrs = ~$43/month |
| Storage | 1 GB × $0.115/GB-month = ~$0.12/month |

**Scale to Zero:** Aurora Serverless v2 now supports 0 ACU with auto-pause on newer PostgreSQL versions, but:
- Resume latency can be 30+ seconds
- Still has minimum storage costs
- Complex to configure correctly

**Verdict:** Overkill for 100 queries/week. Not recommended.

**Sources:**
- [Aurora Serverless v2 Pricing](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.setting-capacity.html)

---

### Option 4: Self-Hosted PostgreSQL on EC2 Spot (RECOMMENDED for lowest cost)

**Cost: ~$2-4/month**

| Instance | Specs | Spot Price | Monthly |
|----------|-------|------------|---------|
| t4g.nano | 0.5 GB RAM | ~$0.0016/hr | ~$1.15/month |
| t4g.micro | 1 GB RAM | ~$0.003/hr | ~$2.20/month |
| **+ EBS gp3** | 20 GB | $0.08/GB-month | ~$1.60/month |

**PostgreSQL Minimum Requirements:**
- Can run with 128-256 MB RAM with tuning
- Your 800 MB data fits easily on 20 GB EBS

**Configuration Tips:**
```
shared_buffers = 64MB
work_mem = 4MB
max_connections = 20
effective_cache_size = 256MB
```

**Pros:**
- Lowest cost option (~$3/month total)
- Full control
- Data in your VPC

**Cons:**
- Spot interruptions (acceptable)
- Manual ops (backups, patching)
- No automatic failover

---

### SQL DB Recommendation

**Primary: RDS Free Tier ($0/month for 12 months)**
- If your AWS account qualifies
- Fully managed, zero ops

**After Free Tier: Self-hosted on EC2 Spot (~$3/month)**
- Lowest ongoing cost
- Co-locate with Qdrant for simplicity

---

## Combined/Bundled Deployment Options

### Option A: Single Lightsail Instance (RECOMMENDED for simplicity)

**Cost: $5-7/month**

| Plan | RAM | vCPU | SSD | Transfer | Monthly |
|------|-----|------|-----|----------|---------|
| 512 MB | 512 MB | 1 | 20 GB | 1 TB | $3.50 |
| **1 GB** | 1 GB | 1 | 40 GB | 2 TB | **$5.00** |
| 2 GB | 2 GB | 1 | 60 GB | 3 TB | $10.00 |

**Can both databases fit on 1 GB RAM?**

| Component | RAM Budget |
|-----------|------------|
| OS + Docker | ~200-300 MB |
| Qdrant (with MMAP) | ~200-300 MB |
| PostgreSQL (tuned) | ~200-300 MB |
| **Total** | ~600-900 MB |

**Answer:** Yes, but tight! The $5/month (1 GB) plan is the minimum recommended. The $7/month (2 GB) plan provides comfortable headroom.

**Pros:**
- Single instance to manage
- Predictable pricing
- No Spot interruptions
- 1-2 TB data transfer included

**Cons:**
- RAM is tight on $5 plan
- Self-managed databases

**Deployment:**
```yaml
# docker-compose.yml for Lightsail
services:
  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - ./qdrant_data:/qdrant/storage
    deploy:
      resources:
        limits:
          memory: 300M
    environment:
      - QDRANT__STORAGE__ON_DISK=true
      - QDRANT__STORAGE__HNSW_ON_DISK=true

  postgresql:
    image: postgres:16-alpine
    volumes:
      - ./pg_data:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          memory: 256M
    command: >
      postgres
      -c shared_buffers=64MB
      -c work_mem=4MB
      -c max_connections=20
```

---

### Option B: EC2 Spot with Both Databases

**Cost: ~$3-5/month**

Same as Option A but using EC2 Spot instead of Lightsail:
- t4g.micro (1 GB): ~$2.20/month Spot + $1.60 EBS = **~$3.80/month**
- t4g.small (2 GB): ~$4.40/month Spot + $1.60 EBS = **~$6.00/month**

**Pros:**
- Slightly cheaper than Lightsail
- More instance type flexibility

**Cons:**
- Spot interruptions (need auto-recovery)
- More complex setup than Lightsail

---

### Option C: Hybrid - Qdrant Cloud + EC2 PostgreSQL

**Cost: ~$3/month**

| Component | Cost |
|-----------|------|
| Qdrant Cloud Free | $0 |
| EC2 Spot t4g.nano + EBS | ~$3 |
| **Total** | **~$3/month** |

**Pros:**
- Lowest possible cost
- Qdrant is fully managed
- PostgreSQL stays in VPC

**Cons:**
- Qdrant data outside VPC
- Two systems to monitor

---

## Cost Comparison Matrix

| Deployment Option | Vector DB | SQL DB | Monthly Cost | Ops Complexity | Best For |
|-------------------|-----------|--------|--------------|----------------|----------|
| **Qdrant Cloud + RDS Free Tier** | Qdrant Cloud ($0) | RDS Free ($0) | **$0** | Low | First 12 months |
| **Qdrant Cloud + EC2 Spot PG** | Qdrant Cloud ($0) | EC2 Spot (~$3) | **~$3** | Medium | Lowest ongoing cost |
| **Single Lightsail $5** | Self-hosted | Self-hosted | **$5** | Medium | Simplicity |
| **Single Lightsail $7** | Self-hosted | Self-hosted | **$7** | Medium | Comfortable headroom |
| **EC2 Spot (both)** | Self-hosted | Self-hosted | **~$4-6** | Medium-High | Cost + Spot comfort |
| **Story 5.1 EC2 t4g.small** | Self-hosted | Self-hosted | **~$5-10** | Medium | Current plan |
| **OpenSearch + RDS** | OpenSearch ($174+) | RDS ($13+) | **$187+** | Low | Not recommended |
| **Aurora Serverless v2** | N/A | Aurora ($43+) | **$43+** | Low | Not recommended |

---

## Final Recommendations

### For Ricardo's RAGLite Deployment

Given the requirements:
- ~100 queries/week (extremely low traffic)
- 129 MB vector data, 800 MB SQL data
- Cost-conscious priority
- Simple AWS CLI deployment
- No guaranteed uptime required

**Recommended Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│  MCP Clients (Claude Desktop, Claude Code)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │ Model Context Protocol (HTTPS)
┌─────────────────────▼───────────────────────────────────────┐
│  AWS Bedrock AgentCore Runtime                              │
│  (FastMCP Server - from existing Story 5.1 research)        │
│  Cost: ~$0/month (free tier for 850 req/month)              │
└─────────────────────┬───────────────────────────────────────┘
                      │ Internal VPC
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
┌───────────────────┐   ┌──────────────────────┐
│ Qdrant Cloud      │   │ PostgreSQL           │
│ FREE TIER         │   │ EC2 Spot t4g.micro   │
│ (129MB / 1GB)     │   │ + 20GB EBS gp3       │
│ $0/month          │   │ ~$3/month            │
└───────────────────┘   └──────────────────────┘

TOTAL: ~$3/month (vs Story 5.1's $14-18/month)
SAVINGS: 75-80% cost reduction!
```

### Alternative: All-in-One Lightsail

If you prefer keeping everything in AWS VPC:

```
┌─────────────────────────────────────────────────────────────┐
│  AWS Bedrock AgentCore Runtime                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│  Amazon Lightsail ($5-7/month)                              │
│  1-2 GB RAM, 1 vCPU, 40-60 GB SSD                          │
│                                                             │
│  ┌─────────────────┐   ┌─────────────────┐                 │
│  │ Qdrant (Docker) │   │ PostgreSQL      │                 │
│  │ with MMAP       │   │ (Docker/native) │                 │
│  └─────────────────┘   └─────────────────┘                 │
└─────────────────────────────────────────────────────────────┘

TOTAL: ~$5-7/month
```

---

## AWS CLI Deployment Commands

### Option 1: Lightsail Single Instance

```bash
# Create Lightsail instance
aws lightsail create-instances \
  --instance-names raglite-db \
  --availability-zone us-east-1a \
  --blueprint-id ubuntu_22_04 \
  --bundle-id micro_3_0 \
  --tags key=Project,value=RAGLite

# Open ports
aws lightsail open-instance-public-ports \
  --instance-name raglite-db \
  --port-info fromPort=6333,toPort=6333,protocol=TCP
aws lightsail open-instance-public-ports \
  --instance-name raglite-db \
  --port-info fromPort=5432,toPort=5432,protocol=TCP

# Allocate static IP
aws lightsail allocate-static-ip --static-ip-name raglite-ip
aws lightsail attach-static-ip \
  --static-ip-name raglite-ip \
  --instance-name raglite-db
```

### Option 2: EC2 Spot Instance

```bash
# Create launch template
aws ec2 create-launch-template \
  --launch-template-name raglite-db-template \
  --launch-template-data '{
    "ImageId": "ami-0c7217cdde317cfec",
    "InstanceType": "t4g.micro",
    "BlockDeviceMappings": [{
      "DeviceName": "/dev/xvda",
      "Ebs": {"VolumeSize": 20, "VolumeType": "gp3"}
    }]
  }'

# Request Spot instance
aws ec2 request-spot-instances \
  --instance-count 1 \
  --launch-specification '{
    "ImageId": "ami-0c7217cdde317cfec",
    "InstanceType": "t4g.micro"
  }'
```

---

## Decision Matrix

| If You Want... | Choose... | Cost |
|----------------|-----------|------|
| **Absolute lowest cost** | Qdrant Cloud Free + EC2 Spot PG | ~$3/month |
| **Simplest single deployment** | Lightsail $5-7/month | ~$5-7/month |
| **All AWS-managed (first year)** | Qdrant Cloud + RDS Free Tier | $0/month |
| **Everything in VPC** | EC2 Spot or Lightsail (both DBs) | ~$4-7/month |
| **Current Story 5.1 plan** | EC2 t4g.small Spot | ~$5-10/month |

---

## Research Sources

### Primary Sources (2025 Data)
- [Qdrant Pricing](https://qdrant.tech/pricing/) - Verified 1GB free tier
- [Qdrant Memory Consumption](https://qdrant.tech/articles/memory-consumption/) - 135MB minimum with MMAP
- [AWS Lightsail Pricing](https://aws.amazon.com/lightsail/pricing/) - $3.50-$10/month plans
- [AWS RDS Free Tier](https://aws.amazon.com/rds/free/) - 750 hours/month db.t3.micro
- [AWS EC2 Spot Pricing](https://aws.amazon.com/ec2/spot/pricing/) - t4g.nano ~$0.0016/hr

### Secondary Sources
- [AWS Database Savings Plans (Dec 2, 2025)](https://aws.amazon.com/about-aws/whats-new/2025/12/database-savings-plans-savings/)
- [Aurora Serverless v2 Zero Capacity](https://www.infoq.com/news/2024/12/aurora-serverless-zero-capacity/)
- [OpenSearch Serverless Half-OCU](https://aws.amazon.com/blogs/big-data/amazon-opensearch-serverless-cost-effective-search-capabilities-at-any-scale/)

---

## Update to Story 5.1

**Recommended Changes:**

1. **Replace EC2 self-hosted Qdrant** with **Qdrant Cloud Free Tier**
   - Reduces ops overhead
   - $0/month vs ~$5/month
   - 129 MB << 1 GB limit

2. **Keep EC2 Spot for PostgreSQL** (current plan is good)
   - Or use RDS Free Tier for first 12 months
   - ~$3/month after free tier

3. **Update cost estimate:**
   - Current Story 5.1: $14-18/month
   - **Revised: $3-7/month** (75-80% savings!)

---

**Research Completed:** 2025-12-05
**Confidence Level:** High (multiple sources validated)
**Next Steps:** Review recommendations with Ricardo and update Story 5.1 accordingly
