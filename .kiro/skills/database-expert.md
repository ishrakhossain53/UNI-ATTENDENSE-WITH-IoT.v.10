# Database Expert Skill

When working with databases:

1. Always use parameterized queries
2. Add indexes for foreign keys
3. Use transactions for multi-step operations
4. Consider query performance
5. Add appropriate constraints
6. Document schema changes
7. Test migrations before applying

## PostgreSQL Best Practices

- Use UUID for primary keys
- Partition large tables by date
- Use connection pooling
- Enable query logging for slow queries
- Regular VACUUM and ANALYZE
- Monitor connection count
- Set appropriate timeouts

## Common Patterns

### Safe Query Pattern
```python
cur.execute(
    "SELECT * FROM users WHERE user_id = %s",
    (user_id,)
)
```

### Transaction Pattern
```python
try:
    conn = db_pool.get_conn()
    cur = conn.cursor()
    # Multiple operations
    conn.commit()
except Exception as e:
    conn.rollback()
    raise
finally:
    cur.close()
    db_pool.put_conn(conn)
```
