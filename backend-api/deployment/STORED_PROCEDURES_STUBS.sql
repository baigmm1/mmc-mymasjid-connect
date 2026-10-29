-- ============================================================================
-- Bank Deposit Batch Stored Procedures - STUB TEMPLATES
-- ============================================================================
-- These are stub/template stored procedures for bank deposit batch operations.
-- Replace the procedure names with your actual procedure names in the utility functions.
--
-- UPDATE THESE:
-- 1. Update procedure names in src/core/bank_deposit_batch_utils.py
-- 2. Implement actual SQL logic based on your database schema
-- 3. Ensure parameters and return values match the expected formats
--
-- ============================================================================


-- ============================================================================
-- sp_CreateBankDepositBatch
-- Creates a new bank deposit batch with transactions as an atomic operation
-- ============================================================================
CREATE PROCEDURE [dbo].[sp_CreateBankDepositBatch]
    @CompanyId INT,
    @ProviderId VARCHAR(50),
    @BatchDate DATETIME,
    @BankDepositDate DATETIME = NULL,
    @BatchStatus INT = 1,
    @BatchMethodType NVARCHAR(20),
    @Amount MONEY,
    @CreatedBy VARCHAR(25),
    @Transactions NVARCHAR(MAX) = NULL  -- JSON array of transactions
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        BEGIN TRANSACTION
        
        -- TODO: Implement batch creation logic
        -- 1. Validate inputs (CompanyId exists, Amount > 0, etc.)
        -- 2. Get next BatchNumber (if using identity)
        -- 3. Insert into BankDepositBatch table
        -- 4. Parse @Transactions JSON and insert each transaction into BankDepositBatchTransactions
        -- 5. Return the created BatchNumber
        
        DECLARE @BatchNumber INT = 0
        
        -- Sample insert logic:
        -- INSERT INTO [dbo].[BankDepositBatch] (
        --     CompanyId, ProviderId, BatchDate, BankDepositDate, BatchStatus, 
        --     BatchMethodType, Amount, CreatedBy, CreatedDate, ModifiedBy, ModifiedDate
        -- ) VALUES (
        --     @CompanyId, @ProviderId, @BatchDate, @BankDepositDate, @BatchStatus,
        --     @BatchMethodType, @Amount, @CreatedBy, GETUTCDATE(), NULL, NULL
        -- )
        -- 
        -- SET @BatchNumber = SCOPE_IDENTITY()
        
        -- Return success
        SELECT 
            1 AS [Success],
            @BatchNumber AS [BatchNumber],
            'Batch created successfully' AS [Message]
        
        COMMIT TRANSACTION
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION
        
        SELECT 
            0 AS [Success],
            NULL AS [BatchNumber],
            ERROR_MESSAGE() AS [Message]
    END CATCH
END
GO


-- ============================================================================
-- sp_GetBankDepositBatch
-- Retrieves a specific batch with all its transactions
-- ============================================================================
CREATE PROCEDURE [dbo].[sp_GetBankDepositBatch]
    @BatchNumber INT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- TODO: Implement batch retrieval logic
        -- 1. Select batch header from BankDepositBatch
        -- 2. Select all transactions for this batch from BankDepositBatchTransactions
        -- 3. Return batch details in first result set, transactions in subsequent rows
        
        -- Sample query:
        -- SELECT 
        --     BatchNumber, CompanyId, ProviderId, BatchDate, BankDepositDate,
        --     BatchStatus, Amount, BatchMethodType, CreatedBy, CreatedDate,
        --     ModifiedBy, ModifiedDate
        -- FROM [dbo].[BankDepositBatch]
        -- WHERE BatchNumber = @BatchNumber
        
        -- SELECT 
        --     CompanyId, BatchNumber, LineNumber, DonationReceiptId, ProviderId,
        --     TransactionType, Amount, CreatedBy, CreatedDate, ModifiedBy, ModifiedDate
        -- FROM [dbo].[BankDepositBatchTransactions]
        -- WHERE BatchNumber = @BatchNumber
        -- ORDER BY LineNumber
        
    END TRY
    BEGIN CATCH
        SELECT 
            'ERROR' AS [ErrorMessage],
            ERROR_MESSAGE() AS [Details]
    END CATCH
END
GO


-- ============================================================================
-- sp_GetBankDepositBatches
-- Retrieves paginated list of batches with optional filtering
-- ============================================================================
CREATE PROCEDURE [dbo].[sp_GetBankDepositBatches]
    @CompanyId INT = NULL,
    @BatchStatus INT = NULL,
    @FromDate DATETIME = NULL,
    @ToDate DATETIME = NULL,
    @Limit INT = 100,
    @Offset INT = 0
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- TODO: Implement filtered batch list retrieval
        -- 1. Build dynamic WHERE clause based on parameters
        -- 2. Apply pagination with OFFSET/FETCH
        -- 3. Return total count in results
        
        -- Sample query:
        -- SELECT 
        --     BatchNumber, CompanyId, ProviderId, BatchDate, BankDepositDate,
        --     BatchStatus, Amount, BatchMethodType, CreatedBy, CreatedDate,
        --     ModifiedBy, ModifiedDate,
        --     COUNT(*) OVER() AS TotalCount
        -- FROM [dbo].[BankDepositBatch]
        -- WHERE 
        --     (@CompanyId IS NULL OR CompanyId = @CompanyId)
        --     AND (@BatchStatus IS NULL OR BatchStatus = @BatchStatus)
        --     AND (@FromDate IS NULL OR BatchDate >= @FromDate)
        --     AND (@ToDate IS NULL OR BatchDate <= @ToDate)
        -- ORDER BY BatchNumber DESC
        -- OFFSET @Offset ROWS FETCH NEXT @Limit ROWS ONLY
        
    END TRY
    BEGIN CATCH
        SELECT 
            'ERROR' AS [ErrorMessage],
            ERROR_MESSAGE() AS [Details]
    END CATCH
END
GO


-- ============================================================================
-- sp_UpdateBankDepositBatch
-- Updates an existing bank deposit batch
-- ============================================================================
CREATE PROCEDURE [dbo].[sp_UpdateBankDepositBatch]
    @BatchNumber INT,
    @BatchDate DATETIME = NULL,
    @BankDepositDate DATETIME = NULL,
    @BatchStatus INT = NULL,
    @BatchMethodType NVARCHAR(20) = NULL,
    @Amount MONEY = NULL,
    @ModifiedBy VARCHAR(25)
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- TODO: Implement batch update logic
        -- 1. Validate BatchNumber exists
        -- 2. Build dynamic UPDATE statement for non-NULL parameters
        -- 3. Update ModifiedDate to GETUTCDATE()
        -- 4. Return success/failure status
        
        -- Sample update logic:
        -- UPDATE [dbo].[BankDepositBatch]
        -- SET 
        --     BatchDate = ISNULL(@BatchDate, BatchDate),
        --     BankDepositDate = ISNULL(@BankDepositDate, BankDepositDate),
        --     BatchStatus = ISNULL(@BatchStatus, BatchStatus),
        --     BatchMethodType = ISNULL(@BatchMethodType, BatchMethodType),
        --     Amount = ISNULL(@Amount, Amount),
        --     ModifiedBy = @ModifiedBy,
        --     ModifiedDate = GETUTCDATE()
        -- WHERE BatchNumber = @BatchNumber
        
        SELECT 
            1 AS [Success],
            'Batch updated successfully' AS [Message]
        
    END TRY
    BEGIN CATCH
        SELECT 
            0 AS [Success],
            ERROR_MESSAGE() AS [Message]
    END CATCH
END
GO


-- ============================================================================
-- sp_DeleteBankDepositBatch
-- Deletes a batch and all its transactions
-- ============================================================================
CREATE PROCEDURE [dbo].[sp_DeleteBankDepositBatch]
    @BatchNumber INT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        BEGIN TRANSACTION
        
        -- TODO: Implement batch deletion logic
        -- 1. Delete transactions for this batch
        -- 2. Delete batch header
        -- 3. Use transactions to ensure atomic operation
        
        -- Sample delete logic:
        -- DELETE FROM [dbo].[BankDepositBatchTransactions]
        -- WHERE BatchNumber = @BatchNumber
        -- 
        -- DELETE FROM [dbo].[BankDepositBatch]
        -- WHERE BatchNumber = @BatchNumber
        
        SELECT 
            1 AS [Success],
            'Batch deleted successfully' AS [Message]
        
        COMMIT TRANSACTION
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION
        
        SELECT 
            0 AS [Success],
            ERROR_MESSAGE() AS [Message]
    END CATCH
END
GO


-- ============================================================================
-- sp_AddBankDepositBatchTransaction
-- Adds a single transaction to an existing batch
-- Used by webhook handlers and transaction processors
-- ============================================================================
CREATE PROCEDURE [dbo].[sp_AddBankDepositBatchTransaction]
    @BatchNumber INT,
    @CompanyId INT,
    @DonationReceiptId INT,
    @ProviderId VARCHAR(50),
    @TransactionType VARCHAR(100),
    @Amount MONEY,
    @CreatedBy INT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- TODO: Implement transaction insertion logic
        -- 1. Validate BatchNumber exists
        -- 2. Get next LineNumber for this batch
        -- 3. Insert into BankDepositBatchTransactions
        -- 4. Return success/failure status
        
        -- Sample insert logic:
        -- DECLARE @NextLineNumber INT = 0
        -- SELECT @NextLineNumber = MAX(LineNumber) + 1 
        -- FROM [dbo].[BankDepositBatchTransactions]
        -- WHERE BatchNumber = @BatchNumber
        -- 
        -- INSERT INTO [dbo].[BankDepositBatchTransactions] (
        --     CompanyId, BatchNumber, LineNumber, DonationReceiptId, ProviderId,
        --     TransactionType, Amount, CreatedBy, CreatedDate
        -- ) VALUES (
        --     @CompanyId, @BatchNumber, @NextLineNumber, @DonationReceiptId,
        --     @ProviderId, @TransactionType, @Amount, @CreatedBy, GETUTCDATE()
        -- )
        
        SELECT 
            1 AS [Success],
            'Transaction added successfully' AS [Message]
        
    END TRY
    BEGIN CATCH
        SELECT 
            0 AS [Success],
            ERROR_MESSAGE() AS [Message]
    END CATCH
END
GO


-- ============================================================================
-- sp_GetBankDepositBatchTransactions
-- Retrieves all transactions for a specific batch
-- ============================================================================
CREATE PROCEDURE [dbo].[sp_GetBankDepositBatchTransactions]
    @BatchNumber INT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- TODO: Implement transaction retrieval logic
        -- 1. Select all transactions for the batch
        -- 2. Order by LineNumber
        
        -- Sample query:
        -- SELECT 
        --     CompanyId, BatchNumber, LineNumber, DonationReceiptId, ProviderId,
        --     TransactionType, Amount, CreatedBy, CreatedDate, ModifiedBy, ModifiedDate
        -- FROM [dbo].[BankDepositBatchTransactions]
        -- WHERE BatchNumber = @BatchNumber
        -- ORDER BY LineNumber
        
    END TRY
    BEGIN CATCH
        SELECT 
            'ERROR' AS [ErrorMessage],
            ERROR_MESSAGE() AS [Details]
    END CATCH
END
GO
