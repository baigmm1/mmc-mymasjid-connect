-- ============================================================================
-- Recurring Transaction Stored Procedures - STUB TEMPLATES
-- ============================================================================
-- These are stub/template stored procedures for recurring transaction sync operations.
-- Replace the procedure logic with your actual implementation.
--
-- Used by: sync_stripe_subscriptions.py script
--
-- UPDATE THESE:
-- 1. Implement actual SQL logic based on your database schema
-- 2. Ensure parameters and return values match the expected formats
-- 3. Add proper error handling and validation
--
-- ============================================================================


-- ============================================================================
-- sp_GetRecurringTransactionsByCompany
-- Retrieves all recurring transactions for a specific company
-- ============================================================================
CREATE PROCEDURE [dbo].[sp_GetRecurringTransactionsByCompany]
    @CompanyId INT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- TODO: Implement query to get all recurring transactions for company
        -- Should return all fields from RecurringTransactions table
        
        SELECT 
            rt.TransactionId,
            rt.CompanyId,
            rt.DonorId,
            rt.ReviewDonorId,
            rt.StartDate,
            rt.Frequency,
            rt.FrequencyCount,
            rt.EndDate,
            rt.ProviderName,
            rt.SubscriptionId,
            rt.PaymentMethod,
            rt.TotalAmount,
            rt.Status,
            rt.CreatedBy,
            rt.CreatedDate,
            rt.ModifiedBy,
            rt.ModifiedDate
        FROM [dbo].[RecurringTransactions] rt
        WHERE rt.CompanyId = @CompanyId
        ORDER BY rt.TransactionId DESC
        
    END TRY
    BEGIN CATCH
        SELECT 
            'ERROR' AS [ErrorMessage],
            ERROR_MESSAGE() AS [Details]
    END CATCH
END
GO


-- ============================================================================
-- sp_CreateRecurringTransaction
-- Creates a new recurring transaction record
-- ============================================================================
CREATE PROCEDURE [dbo].[sp_CreateRecurringTransaction]
    @CompanyId INT,
    @DonorId INT = NULL,
    @StartDate DATETIME,
    @Frequency INT,
    @FrequencyCount INT,
    @EndDate DATETIME = NULL,
    @ProviderName NVARCHAR(50),
    @SubscriptionId NVARCHAR(100),
    @PaymentMethod NVARCHAR(100) = NULL,
    @TotalAmount MONEY,
    @Status INT,
    @CreatedBy INT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        BEGIN TRANSACTION
        
        DECLARE @TransactionId INT = 0
        
        -- TODO: Implement logic to create recurring transaction
        -- 1. Validate inputs (CompanyId exists, SubscriptionId is unique, etc.)
        -- 2. Insert into RecurringTransactions table
        -- 3. Optionally insert related records (RecurringTransactionDetails)
        -- 4. Return the new TransactionId
        
        -- Sample insert logic:
        INSERT INTO [dbo].[RecurringTransactions] (
            CompanyId, 
            DonorId, 
            StartDate, 
            Frequency, 
            FrequencyCount, 
            EndDate,
            ProviderName, 
            SubscriptionId, 
            PaymentMethod, 
            TotalAmount, 
            Status,
            CreatedBy, 
            CreatedDate
        ) VALUES (
            @CompanyId,
            @DonorId,
            @StartDate,
            @Frequency,
            @FrequencyCount,
            @EndDate,
            @ProviderName,
            @SubscriptionId,
            @PaymentMethod,
            @TotalAmount,
            @Status,
            @CreatedBy,
            GETUTCDATE()
        )
        
        SET @TransactionId = SCOPE_IDENTITY()
        
        -- Return success
        SELECT 
            1 AS [Success],
            @TransactionId AS [TransactionId],
            'Recurring transaction created successfully' AS [Message]
        
        COMMIT TRANSACTION
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION
        
        SELECT 
            0 AS [Success],
            NULL AS [TransactionId],
            ERROR_MESSAGE() AS [Message]
    END CATCH
END
GO


-- ============================================================================
-- sp_UpdateRecurringTransaction
-- Updates an existing recurring transaction record
-- ============================================================================
CREATE PROCEDURE [dbo].[sp_UpdateRecurringTransaction]
    @TransactionId INT,
    @EndDate DATETIME = NULL,
    @PaymentMethod NVARCHAR(100) = NULL,
    @TotalAmount MONEY = NULL,
    @Status INT = NULL,
    @ModifiedBy INT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- TODO: Implement logic to update recurring transaction
        -- 1. Validate TransactionId exists
        -- 2. Update only provided (non-NULL) fields
        -- 3. Update ModifiedDate to GETUTCDATE()
        -- 4. Return success/failure status
        
        -- Check if transaction exists
        IF NOT EXISTS (SELECT 1 FROM [dbo].[RecurringTransactions] WHERE TransactionId = @TransactionId)
        BEGIN
            SELECT 
                0 AS [Success],
                'Transaction not found' AS [Message]
            RETURN
        END
        
        -- Sample update logic - only update non-NULL parameters
        UPDATE [dbo].[RecurringTransactions]
        SET 
            EndDate = ISNULL(@EndDate, EndDate),
            PaymentMethod = ISNULL(@PaymentMethod, PaymentMethod),
            TotalAmount = ISNULL(@TotalAmount, TotalAmount),
            Status = ISNULL(@Status, Status),
            ModifiedBy = @ModifiedBy,
            ModifiedDate = GETUTCDATE()
        WHERE TransactionId = @TransactionId
        
        SELECT 
            1 AS [Success],
            'Recurring transaction updated successfully' AS [Message]
        
    END TRY
    BEGIN CATCH
        SELECT 
            0 AS [Success],
            ERROR_MESSAGE() AS [Message]
    END CATCH
END
GO


-- ============================================================================
-- sp_GetRecurringTransactionBySubscriptionId
-- Retrieves a recurring transaction by Stripe SubscriptionId
-- ============================================================================
CREATE PROCEDURE [dbo].[sp_GetRecurringTransactionBySubscriptionId]
    @SubscriptionId NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- TODO: Implement query to get recurring transaction by SubscriptionId
        
        SELECT 
            rt.TransactionId,
            rt.CompanyId,
            rt.DonorId,
            rt.ReviewDonorId,
            rt.StartDate,
            rt.Frequency,
            rt.FrequencyCount,
            rt.EndDate,
            rt.ProviderName,
            rt.SubscriptionId,
            rt.PaymentMethod,
            rt.TotalAmount,
            rt.Status,
            rt.CreatedBy,
            rt.CreatedDate,
            rt.ModifiedBy,
            rt.ModifiedDate
        FROM [dbo].[RecurringTransactions] rt
        WHERE rt.SubscriptionId = @SubscriptionId
        
    END TRY
    BEGIN CATCH
        SELECT 
            'ERROR' AS [ErrorMessage],
            ERROR_MESSAGE() AS [Details]
    END CATCH
END
GO


-- ============================================================================
-- sp_CreateRecurringTransactionDetail
-- Creates transaction detail line items for a recurring transaction
-- ============================================================================
CREATE PROCEDURE [dbo].[sp_CreateRecurringTransactionDetail]
    @TransactionId INT,
    @LineNumber INT,
    @CompanyId INT,
    @DonationType INT,
    @Amount MONEY,
    @Currency VARCHAR(3) = 'USD'
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- TODO: Implement logic to create recurring transaction detail
        -- 1. Validate TransactionId exists
        -- 2. Insert into RecurringTransactionDetails table
        -- 3. Return success/failure status
        
        INSERT INTO [dbo].[RecurringTransactionDetails] (
            TransactionId,
            LineNumber,
            CompanyId,
            DonationType,
            Amount,
            Currency
        ) VALUES (
            @TransactionId,
            @LineNumber,
            @CompanyId,
            @DonationType,
            @Amount,
            @Currency
        )
        
        SELECT 
            1 AS [Success],
            'Transaction detail created successfully' AS [Message]
        
    END TRY
    BEGIN CATCH
        SELECT 
            0 AS [Success],
            ERROR_MESSAGE() AS [Message]
    END CATCH
END
GO


-- ============================================================================
-- sp_GetRecurringTransactionDetails
-- Retrieves all detail line items for a recurring transaction
-- ============================================================================
CREATE PROCEDURE [dbo].[sp_GetRecurringTransactionDetails]
    @TransactionId INT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        SELECT 
            rtd.TransactionId,
            rtd.LineNumber,
            rtd.CompanyId,
            rtd.DonationType,
            rtd.Amount,
            rtd.Currency
        FROM [dbo].[RecurringTransactionDetails] rtd
        WHERE rtd.TransactionId = @TransactionId
        ORDER BY rtd.LineNumber
        
    END TRY
    BEGIN CATCH
        SELECT 
            'ERROR' AS [ErrorMessage],
            ERROR_MESSAGE() AS [Details]
    END CATCH
END
GO


-- ============================================================================
-- Helper: Update recurring transaction status
-- ============================================================================
CREATE PROCEDURE [dbo].[sp_UpdateRecurringTransactionStatus]
    @TransactionId INT,
    @Status INT,
    @ModifiedBy INT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        UPDATE [dbo].[RecurringTransactions]
        SET 
            Status = @Status,
            ModifiedBy = @ModifiedBy,
            ModifiedDate = GETUTCDATE()
        WHERE TransactionId = @TransactionId
        
        SELECT 
            1 AS [Success],
            'Status updated successfully' AS [Message]
        
    END TRY
    BEGIN CATCH
        SELECT 
            0 AS [Success],
            ERROR_MESSAGE() AS [Message]
    END CATCH
END
GO
